---
id: project:fact
type: .fact/specs/Project.md
title: FACT
description: FACT Anchors Contexts and Types — Markdown facts with a .fact control plane
---

# FACT

**FACT Anchors Contexts and Types.**

FACT is a portable, self-describing knowledge format with a deliberately sharp
boundary between semantic knowledge and configuration:

- **facts** are in-scope Markdown documents with YAML frontmatter, outside
  `.fact/`;
- **`.fact/`** is the context control plane: context configuration, type specs,
  policies, adapters, caches, and optional relational declarations;
- other files such as CSV, JSON, images, PDFs, and source code are resources, not
  facts, unless facts reference them or an adapter is explicitly invoked.

Markdown + YAML frontmatter is the preferred authored surface in both planes when
it fits. A Markdown document under `.fact/` remains configuration, not a fact.

A native context is marked by `.fact/` and configured by `.fact/context.md`.
Canonical facts carry stable `id` and `type` frontmatter; locally owned types point
to specifications under `.fact/specs/`.

See [RFC 0009](rfcs/0009-fact.md) for the founding specification.

## Control plane

A typical context may grow toward:

```text
.fact/
  context.md
  ignore
  specs/<name>.md
  specs/<name>.schema.sql
  schema.sql
  adapters/
  cache/
```

Markdown/frontmatter is preferred for human-authored configuration. Specialized
syntax is used only where it earns its existence: ignore patterns, relational SQL,
generated caches, and similar tooling resources.

The control plane never appears in the semantic fact relation.

## Semantic surface

When a tool builds a FACT corpus, graph, or repository mix, its default input is
the in-scope Markdown fact set. Non-Markdown files are opaque resources by
default. A fact can make one relevant by linking to it or naming it in
frontmatter.

The nested example demonstrates this with a CSV account register: the CSV travels
inside the context, while a Markdown `Resource` fact is its semantic entry point.

## From okf-parser to FACT

FACT is independent from OKF, but `franklinbaldo/okf-parser` has already tested
several useful conventions beyond baseline OKF. FACT treats those implementations
as design evidence: mixed-repository ignore semantics, local type specs, optional
per-type and context relational declarations, preview-first staged writes, and
effect-aware tool surfaces.

Implementation details such as language packages and release machinery remain
implementation choices rather than FACT semantics.

## Dogfooding

This repository is itself a native FACT context. The pull-request gate validates
the root and nested contexts, stable ids, the control-plane/fact-plane boundary,
local type resolution, context composition, relative Markdown links, and a
referenced non-Markdown resource that is deliberately not counted as a fact.

Run the same gate locally:

```bash
python scripts/check_dogfooding.py .
```

## Inspirations

[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
inspired Markdown with YAML frontmatter, tolerance for producer-defined fields,
and a deliberately small core. FACT is not an OKF profile or superset;
foreign-format compatibility belongs behind adapters.
