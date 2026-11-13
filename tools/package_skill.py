#!/usr/bin/env python3
"""Build a portable WorkBuddy Skill ZIP, excluding development and private data."""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "pd-rw-research"
SAFE_EXTENSIONS = {".md", ".py", ".json"}


def build(output):
    if not (SKILL / "SKILL.md").is_file():
        raise ValueError("missing SKILL.md")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(SKILL.rglob("*")):
            if file.is_symlink():
                raise ValueError("refusing symlink in Skill: " + str(file))
            if not file.is_file() or file.suffix.lower() not in SAFE_EXTENSIONS:
                continue
            if any(part.startswith(".") or part == "__pycache__" for part in file.relative_to(SKILL).parts):
                continue
            archive.write(file, arcname=str(Path(SKILL.name) / file.relative_to(SKILL)).replace("\\", "/"))
            count += 1
    return output, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "dist" / "pd-rw-research.zip"))
    args = parser.parse_args()
    try:
        path, count = build(args.output)
    except (OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    print("PACKAGE_OK", path, "files=", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
