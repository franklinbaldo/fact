#!/usr/bin/env python3
"""Reference checker for the language-neutral composed-context identity fixture."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "conformance" / "composed-context-identity.json"


def composition_is_valid(context_ids: list[str]) -> bool:
    authored = [context_id.strip() for context_id in context_ids]
    return all(authored) and len(authored) == len(set(authored))


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["contract"] == "composed-context-identity-v1"

    for case in fixture["cases"]:
        actual = all(composition_is_valid(composition) for composition in case["compositions"])
        expected = case["valid"]
        if actual != expected:
            raise AssertionError(
                f"{case['name']}: expected valid={expected}, observed valid={actual}"
            )

    print(f"composed context identity conformance: {len(fixture['cases'])} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
