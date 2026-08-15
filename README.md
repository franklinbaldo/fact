---
id: project:fact
type: .fact/specs/Project.md
title: FACT
description: FACT Anchors Contexts and Types — a portable self-describing knowledge format
---

# FACT

**FACT Anchors Contexts and Types.**

FACT is a portable, self-describing knowledge format built from Markdown facts,
stable context and fact identities, explicit type specifications, and contexts
that compose without flattening their meaning.

A native context is anchored by `.fact/context.yaml`. Canonical facts carry an
`id` and a `type`; locally owned types point to specification facts under
`.fact/specs/`.

See [RFC 0009](rfcs/0009-fact.md) for the founding specification.

## Dogfooding

This repository is itself a native FACT context. The pull-request gate validates
the repository and the nested `examples/minimal` context, including stable ids,
local type resolution, the self-typed `TypeSpecification` bootstrap, composition,
and relative Markdown links.

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
