---
id: type:TypeSpecification
type: .fact/specs/TypeSpecification.md
title: Type Specification
defines: TypeSpecification
---

# Type Specification

A `TypeSpecification` is an ordinary FACT fact that defines the meaning and
expected shape of a type used by facts in the same context.

This specification types itself. That self-reference is the finite bootstrap for
FACT type specifications: a reader can parse the core `id` and `type` fields
before resolving the referenced specification.
