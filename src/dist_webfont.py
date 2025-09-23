import argparse
import os
import shutil

from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import compress as woff2_compress


def get_unicode_ranges(font: TTFont) -> str:
    cmap = font.getBestCmap()
    if not cmap:
        return ""

    codes = sorted(cmap.keys())
    if not codes:
        return ""

    ranges = []
    start = codes[0]
    end = codes[0]

    for code in codes[1:]:
        if code == end + 1:
            end = code
        else:
            if start == end:
                ranges.append(f"U+{start:04X}")
            else:
                ranges.append(f"U+{start:04X}-{end:04X}")
            start = end = code

    if start == end:
        ranges.append(f"U+{start:04X}")
    else:
        ranges.append(f"U+{start:04X}-{end:04X}")

    return ", ".join(ranges)


def get_font_weight(font: TTFont, base_name: str) -> int:
    """从字体名称或 OS/2 表中获取字重值"""
    name_weight_map = {
        "Thin": 100,
        "ExtraLight": 200,
        "Light": 300,
        "Regular": 400,
        "Medium": 500,
        "SemiBold": 600,
        "Bold": 700,
        "ExtraBold": 800,
        "Black": 900,
    }

    # 检查字体文件名中的字重标识
    for name, weight in name_weight_map.items():
        if name.lower() in base_name.lower():
            return weight

    # 从OS/2表获取字重
    if "OS/2" in font:
        os2_weight = font["OS/2"].usWeightClass
        if os2_weight >= 100 and os2_weight <= 900:
            return os2_weight

    # 默认返回常规字重
    return 400


def get_font_style(font: TTFont, base_name: str) -> str:
    """判断字体是否为斜体"""
    if "Italic" in base_name or "Oblique" in base_name:
        return "italic"

    # 从post表检查斜体标志
    if "post" in font and font["post"].italicAngle != 0:
        return "italic"

    return "normal"


def convert_ttf_to_woff(ttf_path: str, output_dir: str) -> tuple:
    font_output_dir = os.path.join(output_dir, "fonts")
    os.makedirs(font_output_dir, exist_ok=True)

    # 获取字体基本信息
    base_name = os.path.splitext(os.path.basename(ttf_path))[0]
    with TTFont(ttf_path) as font:
        family_name = base_name
        # 从名称表获取家族名称
        for record in font["name"].names:
            if record.nameID == 1:  # 家族名称
                family_name = record.toUnicode()
                break

        # 转换为 WOFF
        woff_path = os.path.join(font_output_dir, f"{base_name}.woff")
        font.flavor = "woff"
        font.save(woff_path)

    # 转换为 WOFF2
    woff2_path = os.path.join(font_output_dir, f"{base_name}.woff2")
    with open(ttf_path, "rb") as ttf_file, open(woff2_path, "wb") as woff2_file:
        woff2_compress(ttf_file, woff2_file)

    return family_name, base_name, font_output_dir


def release_css(
    ttf_path: str, output_dir: str, family_name: str, base_name: str, append: bool = False
) -> None:
    """生成或追加CSS内容，支持多字重合并"""
    with TTFont(ttf_path) as font:
        unicode_ranges = get_unicode_ranges(font)
        font_weight = get_font_weight(font, base_name)
        font_style = get_font_style(font, base_name)

    # 构建@font-face规则
    css_rule = f"""@font-face {{
    font-family: '{family_name}';
    src: url('fonts/{base_name}.woff2') format('woff2'),
         url('fonts/{base_name}.woff') format('woff'),
         url('fonts/{base_name}.ttf') format('truetype');
    font-weight: {font_weight};
    font-style: {font_style};
    font-display: swap;
    {'unicode-range: ' + unicode_ranges + ';' if unicode_ranges else ''}
}}
"""

    css_path = os.path.join(output_dir, "style.css")
    # 追加模式（多字重时）或覆盖模式（单字重时）
    mode = "a" if append else "w"
    with open(css_path, mode, encoding="utf-8") as f:
        if append:
            f.write("\n")  # 不同规则间加空行
        f.write(css_rule)


def release_webfont(input_path: str, output_dir: str, append_css: bool = False) -> None:
    """
    转换字体并生成CSS

    参数:
        input_path: 输入TTF文件路径
        output_dir: 输出目录
        append_css: 是否追加到现有CSS（多字重时使用）
    """
    family_name, base_name, font_dir = convert_ttf_to_woff(input_path, output_dir)
    # 复制原始TTF
    shutil.copy(input_path, os.path.join(font_dir, f"{base_name}.ttf"))
    # 生成或追加CSS
    release_css(input_path, output_dir, family_name, base_name, append_css)
    print(f"Web Fonts 成功输出至 {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="将 TTF 字体转换为 WOFF/WOFF2 并生成 CSS（支持多字重）"
    )
    parser.add_argument("input", help="输入 TTF 文件路径")
    parser.add_argument("output", help="输出目录")
    parser.add_argument("--append", action="store_true", help="追加到现有CSS文件（用于多字重）")

    args = parser.parse_args()
    release_webfont(args.input, args.output, args.append)


if __name__ == "__main__":
    main()
