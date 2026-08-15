#!/usr/bin/env python3
"""Deterministic dogfooding gate for the FACT specification repository.

This uses only the Python standard library. It is not a general FACT parser; it
asserts that this repository exercises the native invariants described by RFC
0009, including the fact/control-plane boundary and mixed-repository scope.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

CONTEXT_TYPE = ".fact/specs/Context.md"
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SKIP_DIRS = {".git", "__pycache__"}
LEGACY_CONTROL_SIDECARS = {
    "context.yaml",
    "context.yml",
    "rules.yaml",
    "rules.yml",
    "vocabulary.yaml",
    "vocabulary.yml",
    "adapters.yaml",
    "adapters.yml",
}


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
        if raw[:1].isspace() or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        if key:
            data[key] = scalar(value)
    if not data:
        raise GateError(f"{source}: expected non-empty YAML frontmatter")
    return data


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise GateError(f"{path}: expected YAML frontmatter")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise GateError(f"{path}: unterminated YAML frontmatter") from exc
    return parse_top_level_mapping(lines[1:end], path), text


# `.fact/ignore` deliberately follows the already-proven okf-parser exclusion
# contract: gitignore-like matching plus useful re-inclusion below excluded
# parents. This local copy keeps the FACT dogfood gate dependency-free.
_COMMENT_PREFIX = "#"
_NEGATION_PREFIX = "!"
_ESCAPE = "\\"
_SEPARATOR = "/"
_RECURSIVE_SEGMENT = "**"


@dataclass(frozen=True, slots=True)
class IgnoreRule:
    expression: re.Pattern[str]
    negated: bool
    directory_only: bool

    def matches(self, relative: str, *, is_dir: bool) -> bool:
        if self.directory_only and not is_dir:
            return False
        return self.expression.fullmatch(relative) is not None


def strip_trailing_space(pattern: str) -> str:
    end = len(pattern)
    while end > 0 and pattern[end - 1] == " ":
        escapes = 0
        while end - 2 - escapes >= 0 and pattern[end - 2 - escapes] == _ESCAPE:
            escapes += 1
        if escapes % 2:
            break
        end -= 1
    return pattern[:end]


def class_expression(pattern: str, index: int) -> tuple[str, int] | None:
    end = index + 1
    if end < len(pattern) and pattern[end] in {_NEGATION_PREFIX, "^"}:
        end += 1
    if end < len(pattern) and pattern[end] == "]":
        end += 1
    while end < len(pattern) and pattern[end] != "]":
        end += 1
    if end >= len(pattern):
        return None
    body = pattern[index + 1 : end]
    if body.startswith(_NEGATION_PREFIX):
        body = "^" + body[1:]
    return f"[{body}]", end + 1


def segment_expression(segment: str) -> str:
    expression = ""
    index = 0
    while index < len(segment):
        character = segment[index]
        if character == _ESCAPE and index + 1 < len(segment):
            expression += re.escape(segment[index + 1])
            index += 2
            continue
        if character == "*":
            expression += "[^/]*"
        elif character == "?":
            expression += "[^/]"
        elif character == "[" and (translated := class_expression(segment, index)) is not None:
            expression += translated[0]
            index = translated[1]
            continue
        else:
            expression += re.escape(character)
        index += 1
    return expression


def body_expression(pattern: str) -> str:
    expression = ""
    segments = pattern.split(_SEPARATOR)
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment == _RECURSIVE_SEGMENT:
            expression += ".*" if last else "(?:[^/]+/)*"
            continue
        expression += segment_expression(segment)
        if not last:
            expression += _SEPARATOR
    return expression


@lru_cache(maxsize=512)
def compile_ignore(pattern: str) -> IgnoreRule | None:
    line = strip_trailing_space(pattern)
    if not line or line.startswith(_COMMENT_PREFIX):
        return None
    negated = line.startswith(_NEGATION_PREFIX)
    if negated or (line.startswith(_ESCAPE) and line[1:2] in {_COMMENT_PREFIX, _NEGATION_PREFIX}):
        line = line[1:]
    directory_only = line.endswith(_SEPARATOR) and not line.endswith(_ESCAPE + _SEPARATOR)
    if directory_only:
        line = line[:-1]
    if not line:
        return None
    anchored = _SEPARATOR in line
    body = body_expression(line.removeprefix(_SEPARATOR))
    if not anchored:
        body = f"(?:[^/]+/)*{body}"
    return IgnoreRule(re.compile(body), negated, directory_only)


def iter_ancestors(relative: str):
    segments = relative.split(_SEPARATOR)
    for count in range(1, len(segments) + 1):
        yield _SEPARATOR.join(segments[:count]), count < len(segments)


@dataclass(frozen=True, slots=True)
class IgnoreRules:
    rules: tuple[IgnoreRule, ...]

    @classmethod
    def read(cls, root: Path) -> "IgnoreRules":
        path = root / ".fact" / "ignore"
        if not path.exists():
            return cls(())
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError) as exc:
            raise GateError(f"{path}: cannot read FACT ignore rules: {exc}") from exc
        return cls(tuple(rule for raw in lines if (rule := compile_ignore(raw)) is not None))

    @property
    def has_negation(self) -> bool:
        return any(rule.negated for rule in self.rules)

    def decision(self, relative: str, *, is_dir: bool = False) -> tuple[bool, bool]:
        excluded = False
        reincluded = False
        for ancestor, ancestor_is_dir in iter_ancestors(relative):
            decisive = [
                rule
                for rule in self.rules
                if rule.matches(ancestor, is_dir=ancestor_is_dir or is_dir)
            ]
            if decisive:
                previous = excluded
                excluded = not decisive[-1].negated
                if previous and not excluded:
                    reincluded = True
        return excluded, reincluded


def discover_contexts(base: Path) -> list[Path]:
    contexts: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        here = Path(dirpath)
        if here.name == ".fact" and "context.md" in filenames:
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


def owned_markdown_facts(
    root: Path, contexts: list[Path], ignore: IgnoreRules
) -> tuple[list[Path], int, int]:
    found: list[Path] = []
    ignored = 0
    reincluded = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # `.fact/` is control plane and therefore never even enters fact discovery.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d != ".fact"]
        here = Path(dirpath)
        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            path = (here / name).resolve()
            if owner_of(path, contexts) != root:
                continue
            relative = path.relative_to(root).as_posix()
            excluded, was_reincluded = ignore.decision(relative)
            if excluded:
                ignored += 1
                continue
            if was_reincluded:
                reincluded += 1
            found.append(path)
    return sorted(found), ignored, reincluded


def resolve_reference(source: Path, target: str, context_root: Path) -> Path | None:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
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


def validate_type_spec(spec: Path, root: Path) -> None:
    specs_root = (root / ".fact" / "specs").resolve()
    if not is_below(spec, specs_root):
        raise GateError(f"{spec}: local type specification must live under .fact/specs/")
    data, _ = parse_markdown(spec)
    if data.get("kind") != "type-spec":
        raise GateError(f"{spec}: control-plane type spec needs kind: type-spec")
    if not data.get("name", "").strip():
        raise GateError(f"{spec}: control-plane type spec needs a non-empty name")


def validate_context(root: Path, contexts: list[Path]) -> tuple[str, int, int, int, int, bool]:
    fact_dir = root / ".fact"
    context_path = fact_dir / "context.md"
    if not context_path.is_file():
        raise GateError(f"{root}: missing .fact/context.md")

    for legacy in sorted(LEGACY_CONTROL_SIDECARS):
        if (fact_dir / legacy).exists():
            raise GateError(
                f"{fact_dir / legacy}: dogfooding prefers Markdown/frontmatter for authored control data"
            )

    context, _ = parse_markdown(context_path)
    context_id = context.get("id", "").strip()
    if not context_id:
        raise GateError(f"{context_path}: context control document needs a stable id")
    if context.get("type") != CONTEXT_TYPE:
        raise GateError(f"{context_path}: expected type {CONTEXT_TYPE!r}")

    context_spec = (root / CONTEXT_TYPE).resolve()
    if not context_spec.is_file():
        raise GateError(f"{context_path}: Context control specification does not exist")
    validate_type_spec(context_spec, root)

    specs_root = fact_dir / "specs"
    specs = sorted(specs_root.glob("*.md"))
    if not specs:
        raise GateError(f"{specs_root}: native context needs local type specifications")
    for spec in specs:
        validate_type_spec(spec.resolve(), root)

    ignore = IgnoreRules.read(root)
    facts, ignored_count, reincluded_count = owned_markdown_facts(root, contexts, ignore)
    if not facts:
        raise GateError(f"{root}: native context contains no in-scope FACT facts")

    ids: dict[str, Path] = {}
    non_markdown_resource_refs: set[Path] = set()

    for path in facts:
        if is_below(path, fact_dir.resolve()):
            raise GateError(f"{path}: control-plane Markdown leaked into the fact set")

        data, text = parse_markdown(path)
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
            raise GateError(f"{path}: local type specification belongs to another context: {fact_type}")
        validate_type_spec(spec, root)

        resource = data.get("resource", "").strip()
        if resource:
            resolved = resolve_reference(path, resource, root)
            if resolved is not None:
                if not resolved.exists():
                    raise GateError(f"{path}: referenced resource does not exist: {resource}")
                if resolved.suffix.lower() != ".md":
                    non_markdown_resource_refs.add(resolved)

        for raw_target in LINK_RE.findall(text):
            resolved = resolve_reference(path, raw_target, root)
            if resolved is None:
                continue
            if not resolved.exists():
                raise GateError(
                    f"{path}: unresolved relative Markdown link {raw_target!r} -> {resolved}"
                )
            if resolved.is_file() and resolved.suffix.lower() != ".md":
                non_markdown_resource_refs.add(resolved)

    return (
        context_id,
        len(facts),
        len(specs) + 1,
        len(non_markdown_resource_refs),
        ignored_count,
        ignore.has_negation and reincluded_count > 0,
    )


def main() -> int:
    base = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    contexts = discover_contexts(base)
    if base not in contexts:
        raise GateError(f"{base}: repository root must itself be a native FACT context")
    if len(contexts) < 2:
        raise GateError("complete dogfooding requires at least one nested native context")

    context_ids: dict[str, Path] = {}
    total_facts = 0
    total_control_docs = 0
    total_resource_refs = 0
    total_ignored_markdown = 0
    exercised_reinclusion = False

    for root in contexts:
        (
            context_id,
            fact_count,
            control_doc_count,
            resource_ref_count,
            ignored_count,
            reincluded,
        ) = validate_context(root, contexts)
        if context_id in context_ids:
            raise GateError(
                f"duplicate context id {context_id!r}: {context_ids[context_id]} and {root}"
            )
        context_ids[context_id] = root
        total_facts += fact_count
        total_control_docs += control_doc_count
        total_resource_refs += resource_ref_count
        total_ignored_markdown += ignored_count
        exercised_reinclusion = exercised_reinclusion or reincluded
        label = root.relative_to(base) if root != base else Path(".")
        print(
            f"ok  {label}  {context_id}  {fact_count} facts  {control_doc_count} control docs  "
            f"{resource_ref_count} resource refs  {ignored_count} ignored Markdown"
        )

    if total_resource_refs < 1:
        raise GateError("dogfooding requires a referenced non-Markdown resource outside the fact set")
    if total_ignored_markdown < 1:
        raise GateError("dogfooding requires ignored Markdown outside .fact/")
    if not exercised_reinclusion:
        raise GateError("dogfooding requires .fact/ignore negation to re-include knowledge below an exclusion")

    print(
        f"FACT dogfooding complete: {len(contexts)} contexts, {total_facts} facts, "
        f"{total_control_docs} control docs, {total_resource_refs} referenced resources, "
        f"{total_ignored_markdown} ignored Markdown files"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"FACT dogfooding failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
