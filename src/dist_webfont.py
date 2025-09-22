import argparse
import os
import shutil

from fontTools.ttLib import TTFont
from fontTools.ttLib.sfnt import SFNTWriter
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


def convert_ttf_to_woff(ttf_path: str, output_dir: str) -> tuple:
    font_output_dir = os.path.join(output_dir, "fonts")
    os.makedirs(font_output_dir, exist_ok=True)

    # 获取字体基本信息
    base_name = os.path.splitext(os.path.basename(ttf_path))[0]
    with TTFont(ttf_path) as font:
        family_name = base_name
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


def release_css(ttf_path: str, output_dir: str, family_name: str, base_name: str) -> None:
    with TTFont(ttf_path) as font:
        unicode_ranges = get_unicode_ranges(font)

    css_content = f"""@font-face {{
    font-family: '{family_name}';
    src: url('fonts/{base_name}.woff2') format('woff2'),
         url('fonts/{base_name}.woff') format('woff'),
         url('fonts/{base_name}.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
    font-display: swap;
    {'unicode-range: ' + unicode_ranges + ';' if unicode_ranges else ''}
}}
"""

    css_path = os.path.join(output_dir, "style.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)


def release_webfont(input_path: str, output_dir: str) -> None:
    family_name, base_name, font_dir = convert_ttf_to_woff(input_path, output_dir)
    shutil.copy(input_path, os.path.join(font_dir, f"{base_name}.ttf"))
    release_css(input_path, output_dir, family_name, base_name)
    print(f"Web Fonts 成功输出至 {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="将 TTF 字体转换为 WOFF/WOFF2 并生成 CSS")
    parser.add_argument("input", help="输入 TTF 文件路径")
    parser.add_argument("output", help="输出目录")

    args = parser.parse_args()
    release_webfont(args.input, args.output)

if __name__ == "__main__":
    main()
