import argparse
import math
import os
from typing import Dict, List, Set, Tuple

from fontTools.merge import Merger
from fontTools.subset import Subsetter
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fpdf import FPDF, XPos, YPos


def read_charset(file_path: str) -> Set[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    charset: Set[str] = set()

    for i, line in enumerate(lines):
        if line.startswith("//"):
            continue

        line = line.strip("\n")
        if len(line) != 1:
            raise RuntimeError(f"Charset 中每行仅能有一个字符：line {i}, {line}")
        charset.add(line)

    return charset


def set_meta(font: TTFont, new_names: Dict[str, str]) -> None:
    name_ids = {"family": 1, "style": 2, "full_name": 4, "version": 5, "copyright": 0}

    name_table = font["name"]
    name_type_map = {v: k for k, v in name_ids.items()}

    # 收集原始字体中已有的所有名称记录的平台/语言配置
    existing_configs = {}
    for record in name_table.names:
        name_type = name_type_map.get(record.nameID)
        if not name_type:
            continue

        config_key = (record.platformID, record.platEncID, record.langID, record.nameID)
        existing_configs[config_key] = record

    # 处理需要修改的名称
    for name_type, name_id in name_ids.items():
        if name_type not in new_names or not new_names[name_type]:
            continue

        new_value = new_names[name_type]
        type_configs = [k for k in existing_configs.keys() if k[3] == name_id]

        if type_configs:
            for config in type_configs:
                record = existing_configs[config]
                try:
                    record.string = new_value.encode(record.getEncoding())
                except (UnicodeEncodeError, LookupError):
                    record.string = new_value.encode("utf-16be")
        else:
            # 没有现有配置，创建默认配置（Unicode平台，兼容现代系统）
            print(f"警告: 字体中未找到 {name_type} 的记录，将创建默认配置")
            new_record = NameRecord()
            new_record.nameID = name_id
            new_record.platformID = 0  # Unicode平台
            new_record.platEncID = 3  # Unicode 2.0+
            new_record.langID = 0x0409  # 英语(美国) - 通用默认
            new_record.string = new_value.encode("utf-16be")
            name_table.names.append(new_record)


def get_all_unicode_cmap(font: TTFont) -> Dict[int, str]:
    all_cmap = {}
    for subtable in font["cmap"].tables:
        if subtable.format in (4, 12, 10):
            cmap = subtable.cmap
            all_cmap.update(cmap)
    return all_cmap


def find_chars_in_fonts(
    font_paths: List[str], target_chars: Set[str]
) -> Tuple[Dict[str, Set[str]], Set[str]]:

    font_chars: Dict[str, Set[str]] = {path: set() for path in font_paths}
    remaining_chars = set(target_chars)

    for font_path in font_paths:
        if not remaining_chars:
            break

        with TTFont(font_path) as font:
            cmap = get_all_unicode_cmap(font)

            # 转换为字符集合（便于匹配）
            font_available_chars = {chr(code) for code in cmap.keys()}
            # 找到当前字体中存在的目标字符
            found_chars = remaining_chars.intersection(font_available_chars)
            font_chars[font_path] = found_chars
            # 从剩余字符中移除已找到的
            remaining_chars -= found_chars

    return font_chars, remaining_chars


def subset_from_fonts(args) -> None:
    # 读取目标字符集
    target_chars = read_charset(args.charset)
    print(f"需要查找的字符总数: {len(target_chars)}")

    if not target_chars:
        raise RuntimeError("错误: 字符集文件为空，无法生成字体")

    # 按顺序在多个字体中查找字符
    font_paths = args.input
    font_chars, missing_chars = find_chars_in_fonts(font_paths, target_chars)

    # 处理未找到的字符
    if missing_chars:
        print(f"\n警告: 以下 {len(missing_chars)} 个字符在所有字体中都未找到:")
        for char in sorted(missing_chars):
            try:
                print(f"  字符: '{char}' (编码: U+{ord(char):04X})")
            except:
                pass

    # 检查是否有找到任何字符
    all_found_chars = set()
    for chars in font_chars.values():
        all_found_chars.update(chars)

    if not all_found_chars:
        raise RuntimeError("错误: 没有找到任何有效的字符，无法生成字体")

    print(f"\n总共找到 {len(all_found_chars)} 个字符")

    # 为每个字体创建子集并保存为临时文件
    temp_files = []
    for i, (font_path, chars) in enumerate(font_chars.items()):
        if not chars:
            continue  # 跳过不包含任何所需字符的字体

        font = TTFont(font_path)

        # 转换为字符编码
        char_codes = {ord(char) for char in chars}

        # 保留需要的字符映射
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap = {code: name for code, name in table.cmap.items() if code in char_codes}

        subsetter = Subsetter()
        subsetter.populate(unicodes=char_codes)
        subsetter.subset(font)
        temp_path = f"temp/temp_font_{i}.ttf"
        font.save(temp_path)
        temp_files.append(temp_path)
        font.close()

    if not temp_files:
        raise RuntimeError("错误: 无法创建任何临时字体文件")

    # 合并所有临时字体文件
    merged_font = Merger().merge(temp_files)

    # 设置元数据
    name_args = {
        "family": args.family,
        "style": args.style,
        "full_name": args.full_name,
        "version": args.version,
        "copyright": args.copyright,
    }
    set_meta(merged_font, name_args)

    # 保存最终结果
    merged_font.save(args.output)
    merged_font.close()

    print(f"\n成功生成新字体: {args.output}")
    print(f"保留的字符数量: {len(all_found_chars)}")

    # 清理临时文件
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except:
            pass


def preview_pdf(ttf_path: str, output_dir: str) -> None:
    ttf_name = os.path.splitext(os.path.basename(ttf_path))[0]
    pdf_path = os.path.join(output_dir, f"{ttf_name}.pdf")

    with TTFont(ttf_path) as font:
        cmap = get_all_unicode_cmap(font)

    codes = sorted(cmap.keys())
    # 初始化PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 添加标题
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"{ttf_name} Charset", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(10)

    # 注册当前TTF字体到PDF
    font_id = "custom_font"
    pdf.add_font(font_id, "", ttf_path, uni=True)

    # 表格配置
    chars_per_row = 10
    cell_size = 18
    char_font_size = 28
    code_font_size = 8
    total_chars = len(codes)
    chars_per_page = 12 * chars_per_row
    total_pages = math.ceil(total_chars / chars_per_page)

    for page in range(total_pages):
        if page > 0:
            pdf.add_page()

        start_idx = page * chars_per_page
        end_idx = min((page + 1) * chars_per_page, total_chars)
        page_codes = codes[start_idx:end_idx]

        for i, code in enumerate(page_codes):
            char = chr(code)

            row = i // chars_per_row
            col = i % chars_per_row
            x = 15 + col * cell_size
            y = 40 + row * cell_size

            pdf.rect(x, y, cell_size, cell_size, "D")

            pdf.set_xy(x, y + 2)
            pdf.set_font("Helvetica", "", code_font_size)
            pdf.cell(cell_size, 5, f"U+{code:04X}", align="C")

            pdf.set_xy(x, y + 8)
            pdf.set_font(font_id, "", char_font_size)
            pdf.cell(cell_size, cell_size - 10, char, align="C")

    pdf_path = os.path.join(output_dir, f"{ttf_name}-charset.pdf")
    pdf.output(pdf_path)


def main():
    parser = argparse.ArgumentParser(
        description="从多个字体中按顺序提取指定字符并合并生成新字体",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "input",
        nargs="+",
        help="原始字体文件路径（支持多个，按顺序查找，支持TTF、OTF等）",
    )
    parser.add_argument("charset", help="子集字符文件（每行一个字符）")
    parser.add_argument("output", help="输出的新字体文件路径")

    parser.add_argument("--family", help="字体家族名称")
    parser.add_argument("--style", help="字体样式（如 Regular、Bold、Italic）")
    parser.add_argument("--full-name", help="字体全名")
    parser.add_argument("--version", help="字体版本信息", default="Version 1.0")
    parser.add_argument("--copyright", help="字体版权信息")

    args = parser.parse_args()

    subset_from_fonts(args)
    preview_pdf(args.output, os.path.split(args.output)[0])


if __name__ == "__main__":
    main()
