#!/usr/bin/env python3
"""Check the language-neutral FACT relational capability-boundary fixture."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

FIXTURE = Path("conformance/relational-capability-boundary.json")


def native_view(data: dict[str, object], case: dict[str, object]) -> dict[str, object]:
    files = data["files"]
    assert isinstance(files, dict)

    present_relational = case["present_relational"]
    assert isinstance(present_relational, list)
    for path in present_relational:
        metadata = files.get(path)
        if not isinstance(metadata, dict) or metadata.get("kind") != "relational-control":
            raise ValueError(f"unknown relational control resource: {path}")
        if not PurePosixPath(str(path)).is_relative_to(PurePosixPath(".fact")):
            raise ValueError(f"relational control resource must live below .fact/: {path}")

    facts: list[str] = []
    type_resolution: dict[str, str] = {}
    for path, metadata in files.items():
        if not isinstance(metadata, dict) or metadata.get("kind") != "fact":
            continue
        fact_path = PurePosixPath(path)
        if fact_path.is_relative_to(PurePosixPath(".fact")):
            continue
        facts.append(path)

        type_ref = metadata.get("type")
        if not isinstance(type_ref, str) or not type_ref.startswith(".fact/specs/") or not type_ref.endswith(".md"):
            raise ValueError(f"noncanonical local type reference for {path}: {type_ref!r}")
        spec = files.get(type_ref)
        if not isinstance(spec, dict) or spec.get("kind") != "type-spec":
            raise ValueError(f"missing local type specification for {path}: {type_ref}")
        type_resolution[path] = type_ref

    return {
        "facts": sorted(facts),
        "type_resolution": dict(sorted(type_resolution.items())),
        "requires_sql_execution": False,
    }


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures: list[str] = []
    for case in data["cases"]:
        actual = native_view(data, case)
        expected = {
            "facts": sorted(case["facts"]),
            "type_resolution": dict(sorted(case["type_resolution"].items())),
            "requires_sql_execution": case["requires_sql_execution"],
        }
        if actual != expected:
            failures.append(f"{case['name']}: expected {expected}, got {actual}")

    if failures:
        raise SystemExit("relational capability-boundary conformance failed:\n" + "\n".join(failures))
    print(f"relational capability-boundary conformance: {len(data['cases'])} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
