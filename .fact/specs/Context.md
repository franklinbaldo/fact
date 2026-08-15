---
id: type:Context
type: .fact/specs/TypeSpecification.md
title: Context
---

# Context

A `Context` fact anchors a native FACT context and carries the context's stable
identity in its authored `id`.

The `.fact/` directory establishes the context boundary. Exactly one Markdown
fact directly inside `.fact/` has type `.fact/specs/Context.md`; that fact is the
anchor. Its filename is conventional, not semantic.

Context identity is therefore FACT knowledge expressed as Markdown with YAML
frontmatter, not a separate YAML control document.
