# CKU Specification v1

**Compiled Knowledge Unit (CKU) — Version 1.0**

> A CKU is a structured, machine-readable representation of compiled knowledge
> extracted from a source document. CKUs replace vector embeddings with
> explicit, auditable knowledge structures.

---

## Format

CKUs are serialized as **YAML** files with the `.yaml` extension. Each CKU
represents exactly one source document.

## File Naming

```
{slug}-{hash}.yaml
```

- `slug` — derived from the source filename (lowercase, alphanumeric + hyphens)
- `hash` — first 16 characters of the SHA-256 hash of the source file

Example: `architecture-guide-a3f7b2c1e9d04f58.yaml`

---

## Schema

### Top-Level Structure

```yaml
meta:       # CKUMeta       — REQUIRED
summaries:  # CKUSummary    — REQUIRED
entities:   # CKUEntity[]   — REQUIRED (may be empty)
facts:      # CKUFact[]     — REQUIRED (may be empty)
visuals:    # CKUVisual[]   — REQUIRED (may be empty)
dependencies: # string[]    — REQUIRED (may be empty)
```

### meta (CKUMeta)

| Field      | Type       | Required | Default | Description |
|------------|------------|----------|---------|-------------|
| `source`   | string     | yes      | —       | Path to the original source document |
| `compiled` | datetime   | yes      | —       | ISO 8601 UTC timestamp of compilation |
| `hash`     | string     | yes      | —       | SHA-256 hash prefix (16 chars) of source file |
| `type`     | string     | yes      | —       | Document type: `"markdown"`, `"pdf"`, `"pdf/multimodal"` |
| `language` | string     | no       | `"en"`  | ISO 639-1 language code |
| `access`   | CKUAccess  | no       | `{roles: []}` | Access control |

### meta.access (CKUAccess)

| Field   | Type     | Required | Default | Description |
|---------|----------|----------|---------|-------------|
| `roles` | string[] | no       | `[]`    | Allowed roles. Empty = public (no restriction) |

### summaries (CKUSummary)

| Field      | Type              | Required | Default | Description |
|------------|-------------------|----------|---------|-------------|
| `document` | string            | yes      | —       | One-paragraph holistic document summary |
| `sections` | SectionSummary[]  | no       | `[]`    | Per-section summaries |

### summaries.sections[] (SectionSummary)

| Field     | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `id`      | string | yes      | Short slug identifier |
| `title`   | string | yes      | Section heading |
| `summary` | string | yes      | Concise section summary |

### entities[] (CKUEntity)

| Field       | Type       | Required | Description |
|-------------|------------|----------|-------------|
| `id`        | string     | yes      | Unique slug (e.g., `"entity-1"`) |
| `name`      | string     | yes      | Canonical entity name |
| `type`      | string     | yes      | One of: `person`, `organization`, `system`, `process`, `concept`, `product`, `location`, `event`, `other` |
| `relations` | Relation[] | no       | Relationships to other entities |

### entities[].relations[] (Relation)

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| `target` | string | yes      | Target entity ID (must exist in entities[]) |
| `type`   | string | yes      | Relation label (e.g., `"uses"`, `"extends"`, `"part_of"`) |

### facts[] (CKUFact)

| Field        | Type      | Required | Default | Description |
|--------------|-----------|----------|---------|-------------|
| `id`         | string    | yes      | —       | Unique slug (e.g., `"fact-1"`) |
| `claim`      | string    | yes      | —       | Single self-contained factual statement |
| `source`     | SourceRef | yes      | —       | Source location reference |
| `confidence` | float     | no       | `1.0`   | 0.0–1.0 confidence score |
| `entities`   | string[]  | no       | `[]`    | Referenced entity IDs |

**Confidence scale:**
- `1.0` — explicitly stated in the document
- `0.7–0.9` — strongly implied
- `< 0.7` — inferred from context

### visuals[] (CKUVisual)

| Field             | Type      | Required | Default | Description |
|-------------------|-----------|----------|---------|-------------|
| `id`              | string    | yes      | —       | Unique slug |
| `type`            | string    | yes      | —       | One of: `flowchart`, `table`, `diagram`, `chart`, `image`, `screenshot`, `other` |
| `source`          | SourceRef | yes      | —       | Source location reference |
| `description`     | string    | yes      | —       | Detailed natural-language description |
| `structured_data` | object    | no       | `null`  | Machine-readable representation (e.g., table as JSON) |
| `context`         | string    | no       | `null`  | Surrounding context or caption |

### SourceRef

| Field     | Type    | Required | Default | Description |
|-----------|---------|----------|---------|-------------|
| `page`    | integer | no       | `null`  | 1-based page number |
| `section` | string  | no       | `null`  | Section ID reference |

### dependencies (string[])

List of referenced document IDs or filenames that this CKU depends on.

---

## Constraints

1. All `id` fields within their respective arrays MUST be unique
2. `entities[].relations[].target` MUST reference an existing entity ID
3. `facts[].entities[]` MUST reference existing entity IDs
4. `meta.hash` MUST be the first 16 characters of the SHA-256 hex digest
5. `meta.compiled` MUST be an ISO 8601 UTC timestamp
6. All arrays MAY be empty but MUST be present
7. The `meta` section is generated by the compiler, not by the LLM

---

## Versioning

CKU files do not contain an explicit version field. The version is determined
by the noRAG compiler version that generated them. CKU Spec v1 files are
compatible with noRAG >= 0.1.0.

Future spec versions will maintain backward compatibility where possible.
Breaking changes will increment the major version (v2, v3, etc.).

---

## Example

```yaml
meta:
  source: docs/architecture.md
  compiled: '2026-03-31T12:00:00.000000Z'
  hash: a3f7b2c1e9d04f58
  type: markdown
  language: en
  access:
    roles: []

summaries:
  document: >-
    This document describes the microservice architecture of the platform,
    including service boundaries, communication patterns, and deployment strategy.
  sections:
    - id: service-boundaries
      title: Service Boundaries
      summary: Defines how services are split by domain context.
    - id: communication
      title: Communication Patterns
      summary: Uses async messaging via RabbitMQ and sync REST for queries.

entities:
  - id: entity-1
    name: API Gateway
    type: system
    relations:
      - target: entity-2
        type: routes_to
  - id: entity-2
    name: User Service
    type: system
    relations: []

facts:
  - id: fact-1
    claim: The API Gateway handles all incoming HTTP requests and routes them to downstream services.
    source:
      page: null
      section: communication
    confidence: 1.0
    entities:
      - entity-1
  - id: fact-2
    claim: Services communicate asynchronously via RabbitMQ for event-driven workflows.
    source:
      page: null
      section: communication
    confidence: 0.9
    entities: []

visuals:
  - id: vis-1
    type: diagram
    source:
      page: null
      section: service-boundaries
    description: Architecture diagram showing service dependencies and data flow.
    structured_data: null
    context: null

dependencies: []
```
