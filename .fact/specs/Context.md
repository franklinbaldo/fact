---
kind: type-spec
name: Context
---

# Context

The `Context` control document configures one native FACT context and carries its
stable authored `id`.

A context is discovered by the `.fact/` directory. The conventional control
document is `.fact/context.md`; its location places it in the control plane, so it
is not a FACT fact even though Markdown with YAML frontmatter is used as the
preferred configuration syntax.
