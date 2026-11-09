#!/usr/bin/env python3
"""Hazmat and inspection copies stay identical to the standalone apps, and the hazmat checks still pass."""
import hashlib, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "reference"


def same(rel_a, rel_b):
    a = (ROOT / rel_a).read_bytes()
    b = (ROOT / rel_b).read_bytes()
    if a != b:
        raise SystemExit("not identical: %s vs %s" % (rel_a, rel_b))
    return hashlib.sha256(a).hexdigest()


def main():
    for name in ("engine.js", "index.html", "data.js"):
        digest = same("reference/hazmat-helper/" + name, "android/assets/hazmat/" + name)
        same("reference/hazmat-helper/" + name, "flatpak/app/hazmat/" + name)
        print(name, digest[:12])
    same("reference/inspection/index.html", "android/assets/inspection/index.html")
    same("reference/inspection/index.html", "flatpak/app/inspection/index.html")
    print("inspection html identical")
    engine = ROOT / "reference/hazmat-helper/engine.js"
    data = ROOT / "reference/hazmat-helper/data.js"
    subprocess.check_call(["node", str(ROOT / "tests/hazmat_table_checks.js"), str(engine), str(data)])
    official = ROOT / "reference/hazmat-helper/test.js"
    # The attached test.js also diffs the engine against parsed eCFR JSON that was not in the archive.
    proc = subprocess.run(["node", str(official)], capture_output=True, text=True)
    print("official test.js exit", proc.returncode)
    text = proc.stdout + proc.stderr
    print(text[-800:])
    missing_parse = "hazdata" in text or "Cannot find module" in text
    if proc.returncode != 0 and not missing_parse:
        raise SystemExit("hazmat test.js failed for a reason other than the missing eCFR parse files")
    if proc.returncode == 0:
        print("official test.js passed")
    else:
        print("official test.js needs /workspace/hazdata, which was not attached; table checks above used data.js")


if __name__ == "__main__":
    main()
