import argparse
import math
import os

from fontTools.ttLib import TTFont
from fpdf import FPDF, XPos, YPos

from utils import get_all_unicode_cmap


def preview_pdf(ttf_path: str, pdf_path: str) -> None:
    ttf_name = os.path.splitext(os.path.basename(ttf_path))[0]

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
    pdf.add_font(font_id, "", ttf_path)

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

    pdf.output(pdf_path)


def main():
    parser = argparse.ArgumentParser(
        description="从多个字体中按顺序提取指定字符并合并生成新字体",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("input", help="字体文件路径")
    parser.add_argument("output", help="输出的 PDF 文件路径")

    args = parser.parse_args()

    preview_pdf(args.input, args.output)


if __name__ == "__main__":
    main()
