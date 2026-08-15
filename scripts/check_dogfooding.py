#!/usr/bin/env python3
"""Deterministic dogfooding gate for the FACT specification repository.

This intentionally uses only the Python standard library. It is not a general
FACT parser; it is an executable assertion that this repository exercises the
native invariants described by RFC 0009.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

TYPE_SPEC = ".fact/specs/TypeSpecification.md"
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SKIP_DIRS = {".git", "__pycache__"}


class GateError(Exception):
    pass


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_top_level_mapping(lines: list[str], source: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isspace():
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        if key:
            data[key] = scalar(value)
    if not data:
        raise GateError(f"{source}: expected a non-empty top-level mapping")
    return data


def parse_yaml_sidecar(path: Path) -> dict[str, str]:
    return parse_top_level_mapping(path.read_text(encoding="utf-8").splitlines(), path)


def parse_fact(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise GateError(f"{path}: every in-scope Markdown document needs YAML frontmatter")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise GateError(f"{path}: unterminated YAML frontmatter") from exc
    return parse_top_level_mapping(lines[1:end], path), text


def discover_contexts(base: Path) -> list[Path]:
    contexts: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        here = Path(dirpath)
        if here.name == ".fact" and "context.yaml" in filenames:
            contexts.append(here.parent.resolve())
    return sorted(set(contexts), key=lambda p: (len(p.parts), str(p)))


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def owner_of(path: Path, contexts: list[Path]) -> Path | None:
    candidates = [root for root in contexts if is_below(path, root)]
    if not candidates:
        return None
    return max(candidates, key=lambda root: len(root.parts))


def owned_markdown(root: Path, contexts: list[Path]) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        here = Path(dirpath)
        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            path = (here / name).resolve()
            if owner_of(path, contexts) == root:
                found.append(path)
    return sorted(found)


def resolve_link(source: Path, target: str, context_root: Path) -> Path | None:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    # Markdown permits an optional title after a whitespace-separated target.
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(" ", 1)[0]
    parsed = urlsplit(target)
    if parsed.scheme or target.startswith("//") or target.startswith("#"):
        return None
    clean = unquote(parsed.path)
    if not clean:
        return None
    if clean.startswith("/"):
        return (context_root / clean.lstrip("/")).resolve()
    return (source.parent / clean).resolve()


def validate_context(root: Path, contexts: list[Path]) -> tuple[str, int]:
    marker = root / ".fact" / "context.yaml"
    context = parse_yaml_sidecar(marker)
    context_id = context.get("id", "").strip()
    if not context_id:
        raise GateError(f"{marker}: native contexts need a stable non-empty id")

    rules_ref = context.get("rules")
    if rules_ref:
        rules_path = (root / rules_ref).resolve()
        if not rules_path.is_file():
            raise GateError(f"{marker}: declared rules file does not exist: {rules_ref}")

    bootstrap = root / TYPE_SPEC
    if not bootstrap.is_file():
        raise GateError(f"{root}: missing {TYPE_SPEC} bootstrap specification")

    facts = owned_markdown(root, contexts)
    if not facts:
        raise GateError(f"{root}: native context contains no in-scope facts")

    ids: dict[str, Path] = {}
    fact_data: dict[Path, dict[str, str]] = {}

    for path in facts:
        data, _ = parse_fact(path)
        fact_data[path] = data
        fact_id = data.get("id", "").strip()
        fact_type = data.get("type", "").strip()
        if not fact_id:
            raise GateError(f"{path}: canonical FACT requires a stable id")
        if not fact_type:
            raise GateError(f"{path}: canonical FACT requires a type")
        if fact_id in ids:
            first = ids[fact_id]
            raise GateError(
                f"{root}: duplicate fact id {fact_id!r}: {first.relative_to(root)} and {path.relative_to(root)}"
            )
        ids[fact_id] = path

        if not fact_type.startswith(".fact/specs/") or not fact_type.endswith(".md"):
            raise GateError(
                f"{path}: repository dogfooding requires canonical local type references; got {fact_type!r}"
            )
        spec = (root / fact_type).resolve()
        if not spec.is_file():
            raise GateError(f"{path}: local type specification does not exist: {fact_type}")
        if owner_of(spec, contexts) != root:
            raise GateError(f"{path}: local type specification is not owned by the same context: {fact_type}")

    bootstrap_data = fact_data.get(bootstrap.resolve())
    if bootstrap_data is None:
        raise GateError(f"{bootstrap}: bootstrap specification is not an ordinary in-scope fact")
    if bootstrap_data.get("type") != TYPE_SPEC:
        raise GateError(f"{bootstrap}: TypeSpecification must exercise the finite self-typing bootstrap")

    for path, data in fact_data.items():
        if is_below(path, (root / ".fact" / "specs").resolve()):
            if data.get("type") != TYPE_SPEC:
                raise GateError(f"{path}: every local type specification must itself be a TypeSpecification fact")

        _, text = parse_fact(path)
        for raw_target in LINK_RE.findall(text):
            resolved = resolve_link(path, raw_target, root)
            if resolved is not None and not resolved.exists():
                raise GateError(
                    f"{path}: unresolved relative Markdown link {raw_target!r} -> {resolved}"
                )

    return context_id, len(facts)


def main() -> int:
    base = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    contexts = discover_contexts(base)
    if base not in contexts:
        raise GateError(f"{base}: repository root must itself be a native FACT context")
    if len(contexts) < 2:
        raise GateError("complete dogfooding requires at least one nested native context")

    context_ids: dict[str, Path] = {}
    total_facts = 0
    for root in contexts:
        context_id, count = validate_context(root, contexts)
        if context_id in context_ids:
            raise GateError(
                f"duplicate context id {context_id!r}: {context_ids[context_id]} and {root}"
            )
        context_ids[context_id] = root
        total_facts += count
        print(f"ok  {root.relative_to(base) if root != base else Path('.')}  {context_id}  {count} facts")

    print(f"FACT dogfooding complete: {len(contexts)} contexts, {total_facts} canonical facts")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"FACT dogfooding failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
