#!/usr/bin/env python3
"""检查 registry.json 中所有技能是否正确声明了平台支持."""

import json
import sys
from pathlib import Path

REGISTRY = Path(__file__).parent.parent / "registry.json"
REQUIRED_PLATFORMS = {"windows", "linux", "macos"}


def main() -> int:
    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)

    errors = []
    for skill in registry.get("skills", []):
        skill_path = Path(skill["path"]) / "skill.json"
        if not skill_path.exists():
            errors.append(f"Missing skill.json: {skill_path}")
            continue

        with open(skill_path, encoding="utf-8") as f:
            manifest = json.load(f)

        platforms = manifest.get("platform_compatibility", {})
        missing = REQUIRED_PLATFORMS - set(platforms.keys())
        if missing:
            errors.append(f"{skill['name']}: missing platform_compatibility keys {missing}")

    if errors:
        print("Platform compatibility check failed:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("All skills have valid platform compatibility declarations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
