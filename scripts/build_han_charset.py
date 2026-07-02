import argparse
from pathlib import Path
from typing import Iterable, Set


EXT_B_START = 0x20000
EXT_B_END = 0x2A6DF


def is_ext_b(char: str) -> bool:
    codepoint = ord(char)
    return EXT_B_START <= codepoint <= EXT_B_END


def read_ext_b_from_tsv_dir(tsv_dir: Path) -> Set[str]:
    if not tsv_dir.is_dir():
        raise RuntimeError(f"TSV 目录不存在：{tsv_dir}")

    charset: Set[str] = set()

    for path in sorted(tsv_dir.rglob("*.tsv")):
        text = path.read_text(encoding="utf-8")
        charset.update(char for char in text if is_ext_b(char))

    return charset


def read_extra_charset(path: Path) -> Set[str]:
    charset: Set[str] = set()

    for i, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if raw_line.startswith("//"):
            continue

        line = raw_line.strip()
        if not line:
            continue
        if len(line) != 1:
            raise RuntimeError(f"额外字符集每行仅能有一个字符：{path}:{i}: {line}")
        charset.add(line)

    return charset


def write_charset(output: Path, charset: Iterable[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sorted(set(charset), key=ord)), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 TSV 目录提取扩展 B 字符，并与额外字符集合并输出。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("tsv_dir", help="包含 TSV 文件的目录")
    parser.add_argument("output", help="输出字符集文件路径")
    parser.add_argument(
        "--extra-charset",
        action="append",
        default=[],
        help="额外字符集文件路径（每行一个字符，可重复传入）",
    )
    args = parser.parse_args()

    charset = read_ext_b_from_tsv_dir(Path(args.tsv_dir))
    for extra_path in args.extra_charset:
        charset.update(read_extra_charset(Path(extra_path)))

    write_charset(Path(args.output), charset)
    print(f"字符集输出完成：{args.output}")
    print(f"扩展 B 与额外字符合并后共 {len(charset)} 个字符")


if __name__ == "__main__":
    main()
