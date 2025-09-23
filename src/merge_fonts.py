import argparse

from fontTools.merge import Merger

from utils import set_meta


def merge_fonts(args):
    merger = Merger()
    merged_font = merger.merge(args.input)

    name_args = {
        "family": args.family,
        "style": args.style,
        "full_name": args.full_name,
        "version": args.version,
        "copyright": args.copyright,
    }
    set_meta(merged_font, name_args)

    merged_font.save(args.output)
    print(f"字体合并完成，输出路径：{args.output}")

    merged_font.close()


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
    parser.add_argument("output", help="输出的新字体文件路径")

    parser.add_argument("--family", help="字体家族名称")
    parser.add_argument("--style", help="字体样式（如 Regular、Bold、Italic）")
    parser.add_argument("--full-name", help="字体全名")
    parser.add_argument("--version", help="字体版本信息", default="Version 1.0")
    parser.add_argument("--copyright", help="字体版权信息")

    args = parser.parse_args()

    merge_fonts(args)


if __name__ == "__main__":
    main()
