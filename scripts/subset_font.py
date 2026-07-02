import argparse
import os
import tempfile
from typing import Dict, List, Set, Tuple

from fontTools.merge import Merger
from fontTools.subset import Subsetter
from fontTools.ttLib import TTFont

from utils import get_all_unicode_cmap, set_meta


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
    with tempfile.TemporaryDirectory(prefix="subset_font_") as temp_dir:
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
                    table.cmap = {
                        code: name for code, name in table.cmap.items() if code in char_codes
                    }

            subsetter = Subsetter()
            subsetter.populate(unicodes=char_codes)
            subsetter.subset(font)
            temp_path = os.path.join(temp_dir, f"temp_font_{i}.ttf")
            font.save(temp_path)
            temp_files.append(temp_path)
            font.close()

        if not temp_files:
            raise RuntimeError("错误: 无法创建任何临时字体文件")

        # 合并所有临时字体文件；只有一个输入时直接重新打开该临时字体
        if len(temp_files) > 1:
            merged_font = Merger().merge(temp_files)
        else:
            merged_font = TTFont(temp_files[0])

        # 设置元数据
        name_args = {
            "family": args.family,
            "style": args.style,
            "full_name": args.full_name,
            "version": args.version,
            "copyright": args.copyright,
        }
        if any(value is not None for value in name_args.values()):
            set_meta(merged_font, name_args)

        # 保存最终结果
        merged_font.save(args.output)
        merged_font.close()

    print(f"\n成功生成新字体: {args.output}")
    print(f"保留的字符数量: {len(all_found_chars)}")


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


if __name__ == "__main__":
    main()
