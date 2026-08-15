---
kind: type-spec
name: Resource
---

# Resource

A `Resource` fact gives semantic meaning to a non-Markdown file carried by the
context.

The example field `resource` is a path resolved from the fact document that
carries it. The referenced bytes remain a resource rather than being promoted to
a FACT fact. This specification is control-plane Markdown under `.fact/`.
