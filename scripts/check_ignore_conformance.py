#!/usr/bin/env python3
"""Run the language-neutral `.fact/ignore` conformance fixture."""

from __future__ import annotations

import json
from pathlib import Path

from check_dogfooding import IgnoreRules, compile_ignore


def main() -> int:
    fixture_path = Path("conformance/ignore.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("version") != 1:
        raise AssertionError(f"unsupported fixture version: {fixture.get('version')!r}")

    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        raise AssertionError("ignore conformance fixture needs at least one case")

    for case in cases:
        patterns = case["patterns"]
        rules = IgnoreRules(
            tuple(rule for pattern in patterns if (rule := compile_ignore(pattern)) is not None)
        )
        excluded, reincluded = rules.decision(case["path"], is_dir=case.get("is_dir", False))
        expected = (case["excluded"], case["reincluded"])
        observed = (excluded, reincluded)
        if observed != expected:
            raise AssertionError(
                f"{case['name']}: expected excluded/reincluded={expected}, got {observed}"
            )
        print(f"ok  {case['name']}")

    print(f"FACT ignore conformance complete: {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
