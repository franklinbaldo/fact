#!/usr/bin/env python3
"""Check the language-neutral FACT local type-resolution fixture."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

FIXTURE = Path("conformance/local-type-resolution.json")


def is_below(path: PurePosixPath, root: PurePosixPath) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def owner_of(path: PurePosixPath, contexts: list[PurePosixPath]) -> PurePosixPath | None:
    candidates = [root for root in contexts if is_below(path, root)]
    return max(candidates, key=lambda root: len(root.parts)) if candidates else None


def is_absolute_uri(value: str) -> bool:
    """Return whether a type reference is an absolute URI without dereferencing it."""
    return bool(urlsplit(value).scheme)


def resolve(case: dict[str, object], contexts: list[PurePosixPath], specs: dict[str, dict[str, str]]) -> dict[str, object]:
    fact = PurePosixPath(str(case["fact"]))
    type_ref = str(case["type"])
    owner = owner_of(fact, contexts)
    if owner is None:
        return {"valid": False, "error": "no-owning-context"}
    if is_absolute_uri(type_ref):
        return {
            "valid": True,
            "owner": owner.as_posix(),
            "spec": type_ref,
        }
    if not type_ref.startswith(".fact/specs/") or not type_ref.endswith(".md"):
        return {"valid": False, "error": "noncanonical-type-reference"}

    spec = (owner / type_ref) if str(owner) != "." else PurePosixPath(type_ref)
    metadata = specs.get(spec.as_posix())
    if metadata is None:
        return {"valid": False, "error": "missing-local-spec"}
    if metadata.get("kind") != "type-spec" or not metadata.get("name", "").strip():
        return {"valid": False, "error": "invalid-type-spec"}
    return {
        "valid": True,
        "owner": owner.as_posix(),
        "spec": spec.as_posix(),
    }


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    contexts = [PurePosixPath(path) for path in data["contexts"]]
    specs = data["specs"]
    failures: list[str] = []
    for case in data["cases"]:
        actual = resolve(case, contexts, specs)
        expected = {key: case[key] for key in ("valid", "owner", "spec", "error") if key in case}
        if actual != expected:
            failures.append(f"{case['name']}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("local type-resolution conformance failed:\n" + "\n".join(failures))
    print(f"local type-resolution conformance: {len(data['cases'])} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
