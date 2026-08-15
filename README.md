---
id: project:fact
type: .fact/specs/Project.md
title: FACT
description: FACT Anchors Contexts and Types — a portable self-describing knowledge format
---

# FACT

**FACT Anchors Contexts and Types.**

FACT is a portable, self-describing knowledge format built around one canonical
semantic surface: **Markdown with YAML frontmatter**.

A context may contain any files — CSV, JSON, source code, images, PDFs, and other
resources. Their presence makes them files in the context, not FACT facts. FACT
interprets Markdown facts; those facts may reference other files when the files
matter semantically.

A native context is marked by `.fact/` and anchored by an ordinary Markdown fact
of type `.fact/specs/Context.md`. Canonical facts carry an `id` and a `type`;
locally owned types point to specification facts under `.fact/specs/`.

See [RFC 0009](rfcs/0009-fact.md) for the founding specification.

## Semantic surface

When a tool builds a FACT corpus, graph, or repository mix, its default semantic
input is the in-scope Markdown facts. Non-Markdown files are opaque resources by
default: they are not promoted into the fact set merely because they are present.
A fact can make one relevant by linking to it or naming it in frontmatter.

The nested example demonstrates this with a CSV account register: the CSV travels
inside the context, while a Markdown `Resource` fact is its semantic entry point.

## Dogfooding

This repository is itself a native FACT context. The pull-request gate validates
the repository and the nested `examples/minimal` context, including stable ids,
local type resolution, the self-typed `TypeSpecification` bootstrap, context
composition, relative Markdown links, and a referenced non-Markdown resource that
is deliberately not counted as a fact.

Run the same gate locally:

```bash
python scripts/check_dogfooding.py .
```

## Inspirations

FACT is an independent specification. [Open Knowledge Format
(OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
inspired the use of Markdown with YAML frontmatter, tolerance for producer-defined
fields, and a deliberately small core. FACT is not an OKF profile or superset;
foreign-format compatibility belongs behind adapters.
