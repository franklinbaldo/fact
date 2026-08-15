---
id: type:Resource
type: .fact/specs/TypeSpecification.md
title: Resource
---

# Resource

A `Resource` fact points to or describes bytes that are not themselves FACT facts,
such as CSV, JSON, images, PDFs, or source files.

A resource may live inside the context and appear in its file list. It enters the
semantic FACT surface through a Markdown fact that references it; mere filesystem
presence never promotes it into the fact set.
