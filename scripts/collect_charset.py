import argparse
from pathlib import Path
from typing import Iterable, Set


UNICODE_BLOCKS = {
    "ext-b": (0x20000, 0x2A6DF),
}


def iter_input_files(inputs: Iterable[str]) -> Iterable[Path]:
    for input_path in inputs:
        path = Path(input_path)
        if path.is_dir():
            yield from sorted(child for child in path.rglob("*") if child.is_file())
        elif path.is_file():
            yield path
        else:
            raise RuntimeError(f"输入路径不存在：{path}")


def should_keep_char(char: str, block: str | None) -> bool:
    if block is None:
        return True

    start, end = UNICODE_BLOCKS[block]
    codepoint = ord(char)
    return start <= codepoint <= end


def collect_charset(args) -> None:
    charset: Set[str] = set()

    for path in iter_input_files(args.input):
        text = path.read_text(encoding="utf-8").replace("\n", "")
        charset.update(char for char in text if should_keep_char(char, args.unicode_block))

    sorted_charset = sorted(charset, key=lambda char: ord(char))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_charset))

    print(f"字符集输出完成：{args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="从文本中收集唯一字符生成字符集",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("input", nargs="+", help="内容文本或目录路径（支持多个）")
    parser.add_argument("output", help="输出的新字体文件路径")
    parser.add_argument(
        "--unicode-block",
        choices=sorted(UNICODE_BLOCKS.keys()),
        help="仅收集指定 Unicode 区块中的字符",
    )

    args = parser.parse_args()

    collect_charset(args)


if __name__ == "__main__":
    main()
