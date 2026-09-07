---
id: rfc:0010
type: .fact/specs/RFC.md
title: Composed context identity
status: accepted
description: Clarifies that context ids must be unique within one composed FACT surface so (context_id, fact_id) remains an unambiguous stable key
---

# RFC 0010: Composed context identity

## Summary

RFC 0009 defines `context.id` as stable authored identity and defines a fact's stable key in a composed surface as `(context_id, fact_id)`. The repository dogfood gate already rejects duplicate context ids, but RFC 0009 does not state that composition invariant explicitly.

This RFC closes that gap without introducing a global registry.

## Decision

Within one composed FACT surface, every native context `id` MUST be unique.

The scope is the composition being opened or validated, not the world. Two independent FACT trees may use the same context id without contacting a registry; they conflict only when a reader attempts to compose them into the same surface.

This preserves the authored identity model from RFC 0009:

- context identity is not derived from path, Git remote, repository URL, hostname, or checkout location;
- fact ids remain unique only within their owning context;
- `(context_id, fact_id)` remains an unambiguous stable key in a composed surface;
- nesting or vendoring does not rewrite either authored id to manufacture uniqueness.

A duplicate context id in one composition is therefore an `error`, not a warning and not an instruction to mint a path-derived replacement.

## Conformance

`conformance/composed-context-identity.json` is the language-neutral fixture for this rule. It covers:

1. distinct context ids in one composition — valid;
2. the same authored context id appearing twice in one composition — invalid;
3. the same context id reused in two independent compositions — valid, because FACT establishes no global registry.

The reference checker is intentionally dependency-free. Implementations may use any internal representation as long as they produce the same observable result.

## Relationship to RFC 0009

This is a clarification of RFC 0009 sections 3, 4 and 8, not a new identity layer. RFC 0009 remains the founding specification; this RFC makes explicit an invariant its executable dogfood gate already enforced.

No network lookup, registry, path hashing, repository identity, or implementation-specific engine becomes part of native conformance.
