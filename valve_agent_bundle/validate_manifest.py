#!/usr/bin/env python3
"""Validate a static task manifest and print topological groups. No CAD/CAE jobs are launched."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def validate(path: Path) -> list[list[str]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    tasks = doc.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a nonempty list")
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ID")
    known = set(ids)
    required = {"id","name","owner","depends_on","action","output","acceptance_check","resource_pool","when","write_scope"}
    for t in tasks:
        missing = required - t.keys()
        if missing:
            raise ValueError(f"{t.get('id')}: missing {sorted(missing)}")
        if t["owner"] not in doc["roles"]:
            raise ValueError(f"{t['id']}: unknown owner")
        if t["resource_pool"] not in doc["resource_pools"]:
            raise ValueError(f"{t['id']}: unknown resource pool")
        if not t["write_scope"].startswith("runs/") or ".." in t["write_scope"].split("/"):
            raise ValueError(f"{t['id']}: unsafe workspace")
        unknown = set(t["depends_on"]) - known
        if unknown or t["id"] in t["depends_on"]:
            raise ValueError(f"{t['id']}: invalid dependency {unknown}")
    pending = {t["id"]:set(t["depends_on"]) for t in tasks}
    done: set[str] = set()
    levels: list[list[str]] = []
    while pending:
        ready = sorted(k for k,v in pending.items() if v <= done)
        if not ready:
            raise ValueError("cyclic dependency detected")
        levels.append(ready)
        done.update(ready)
        for k in ready:
            del pending[k]
    return levels

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=Path(__file__).with_name("tasks.json"))
    args = parser.parse_args()
    try:
        levels = validate(args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Manifest OK: {sum(map(len, levels))} task templates; no dependency cycles.")
    print("These groups are topological layers, not a resource-aware execution schedule.")
    for index,group in enumerate(levels,1):
        print(f"L{index:02}: {', '.join(group)}")
    print("Engineering readiness, conditional waivers, numerical validity, licensing and real inputs are NOT validated.")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
