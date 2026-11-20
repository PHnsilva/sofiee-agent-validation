# Consumer rule bundle

## Contract

`validation.inspectConsumerRuleBundle` accepts one bounded bundle containing consumer-declared metadata, versioned documents and rules. The bundle and every document/rule carry an identifier, version, origin and scope. Document contents and rule definitions are strings; the runtime does not interpret them as executable instructions.

Each document is limited to 4,000 characters and each bundle to five documents. Each rule definition is limited to 1,000 characters and each bundle to twenty rules. These limits bound one request; a bundle is not persisted between calls.

## Conflict behavior

The identity of a document or rule is its kind, identifier, version and scope. Repeated identities with different declared origins or content produce `status: conflict`. The result retains the entries and reports conflicts without selecting a winner. Identical repeated entries are retained and do not create a conflict.

Documents are returned with a SHA-256 digest instead of their content. Rule definitions are returned unchanged with a digest so a later domain operation can interpret them under its own contract. The receipt operation does not apply the definitions.

## Trust and authority

Origin, version and scope are declarations; the runtime does not fetch sources or authenticate their publisher. Document content is hashed but not parsed, executed, or used to alter permissions. The result reports `provenance: declared_only` and `authority: none`. A structurally received bundle does not prove that its claims are true or authorize access to a consumer system.

The operation is stateless and has no connector, filesystem access, permission control or persistent storage. Applying consumer rules to fields and relationships is a separate domain behavior.
