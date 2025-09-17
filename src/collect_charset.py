import argparse


def collect_charset(args) -> None:
    with open(args.input, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text = "".join(lines).replace("\n", "")
    charset = set(text)

    sorted_charset = sorted(charset, key=lambda char: ord(char))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_charset))

    print(f"字符集输出完成：{args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="从文本中收集唯一字符生成字符集",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("input", help="内容文本路径")
    parser.add_argument("output", help="输出的新字体文件路径")

    args = parser.parse_args()

    collect_charset(args)


if __name__ == "__main__":
    main()
