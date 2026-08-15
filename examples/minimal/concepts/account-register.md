---
id: resource:account-register
type: .fact/specs/Resource.md
title: Account register
resource: ../data/accounts.csv
---

# Account register

The example keeps its account register as an ordinary CSV resource. The CSV is a
file in the context and can appear in a context file listing, but it is not a FACT
fact and is not part of the default semantic corpus.

This Markdown fact is the semantic entry point. A consumer that needs the bytes
can follow [the referenced CSV](../data/accounts.csv); a repository mix that only
combines FACT facts ignores the CSV unless resource following is requested.
