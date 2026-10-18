"""Command line: ``python -m obscura_open25 verify FOLDER [--chips N]``."""
import sys

from .verify import verify_folder


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != "verify":
        print("usage: python -m obscura_open25 verify FOLDER [--chips N]")
        return 2
    folder, n = argv[1], None
    if "--chips" in argv:
        n = int(argv[argv.index("--chips") + 1])
    problems = verify_folder(folder, chip_sample=n)
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(" ", p)
        return 1
    print("everything matches the published checksums and tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
