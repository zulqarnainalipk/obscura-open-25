"""Command line.

    python -m obscura_open25 verify FOLDER [--chips N]     files against the published checksums
    python -m obscura_open25 qc FOLDER [--out DIR]         validation of the record (writes qc_results.json, qc_coverage.png)
"""
import sys

from .verify import verify_folder

USAGE = __doc__


def _verify(argv):
    folder, n = argv[0], None
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


def _qc(argv):
    from .dataset import Dataset
    from .qc import write_qc

    out = argv[argv.index("--out") + 1] if "--out" in argv else "qc_output"
    result = write_qc(Dataset(argv[0]), out, signal="--no-signal" not in argv)
    passed = sum(result["checks"].values())
    print(f"georeferencing: {result['georef']}")
    print(f"consistency checks passed: {passed} of {len(result['checks'])}")
    for issue in result["issues"]:
        print("  ISSUE:", issue)
    print(f"written to {out}")
    return 1 if result["issues"] else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in ("verify", "qc"):
        print(USAGE)
        return 2
    return {"verify": _verify, "qc": _qc}[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
