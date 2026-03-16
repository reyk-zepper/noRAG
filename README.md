# noRAG

> **Compile documents into machine-optimized knowledge. No vectors. No chunks. No embeddings. Just understanding.**

---

**[Deutsch](#deutsch)** | **[English](#english)**

---

## Deutsch

### Was ist noRAG?

noRAG ist ein **Knowledge Compiler**. So wie ein Compiler Quellcode in Maschinencode uebersetzt, uebersetzt noRAG Dokumente in **maschinenoptimiertes Wissen**.

Der Name sagt es: **no RAG** — kein Retrieval Augmented Generation. Stattdessen ein fundamental anderer Ansatz:

**Compile, don't search.**

### Das Problem mit RAG

RAG (Retrieval Augmented Generation) ist der aktuelle Standard, um LLMs Zugriff auf externes Wissen zu geben. Aber RAG hat strukturelle Schwaechen:

- **Pipeline-Komplexitaet** — Chunking, Embedding, Vector DB, Reranking: zu viele fragile Teile
- **Retrieval-Qualitaet** — Vektorsuche findet oft das Falsche oder verliert Kontext
- **Visuelles Wissen** — Enterprise-Dokumente enthalten Diagramme, Tabellen, Flowcharts. RAG ignoriert diese komplett
- **Kontextverlust** — Chunking zerstoert den Zusammenhang zwischen Text, Bildern und Layout

### noRAGs Ansatz

|  | RAG | noRAG |
|---|---|---|
| **Wann** | Zur Laufzeit (bei jeder Frage) | Zur Compile-Zeit (einmal bei Aufnahme) |
| **Was** | Textfragmente suchen | Dokument holistisch verstehen |
| **Wie** | Vektoraehnlichkeit (fuzzy) | Wissensstruktur navigieren (exakt) |
| **Visuelles** | Wird ignoriert | First-Class-Citizen |
| **Ergebnis** | Rohe Chunks im Prompt | Kompiliertes, minimales Wissen |

### Wie funktioniert es?

```
Dokument  ──▶  Parser  ──▶  LLM Compiler  ──▶  CKU (YAML)  ──▶  Knowledge Map (SQLite)
                                                                        │
Frage     ──▶  Router  ──▶  Assembler  ──▶  LLM  ──▶  Antwort  ◀──────┘
```

1. **Compile**: Ein multimodales LLM liest jedes Dokument holistisch und extrahiert eine **Compiled Knowledge Unit (CKU)** — Fakten, Entitaeten, Beziehungen, visuelle Inhalte, Zusammenfassungen
2. **Index**: Entitaeten und Fakten werden in einer SQLite-Wissenskarte indiziert
3. **Query**: Bei einer Frage wird die Wissensstruktur navigiert (nicht durchsucht), minimaler Kontext assembliert, und ein LLM antwortet mit exakten Quellenangaben

**Kein Vector Store. Keine Embeddings. Kein Chunking. Keine Similarity Search.**

### Quickstart

```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY="sk-ant-..."

# Dokumente kompilieren
norag compile ./documents/

# Fragen stellen
norag query "Wie laeuft das Onboarding in der ersten Woche?"
```

### Ausfuehrliche Testanleitung

Siehe [docs/testing.md](docs/testing.md) fuer eine vollstaendige Anleitung mit Demo-Szenarien, CLI-Referenz und Erklaerung was bei Compile und Query passiert.

### Tech Stack

- **Python 3.10+** mit Pydantic v2, Typer, Rich
- **CKU-Format**: YAML-Dateien — human-readable, git-versionierbar
- **Knowledge Map**: SQLite mit FTS5 Volltext-Suche
- **PDF-Parser**: PyMuPDF (Bilder, Tabellen, Diagramme)
- **LLM**: Model-agnostisch — Claude API oder Ollama (lokal)

### Roadmap

| Version | Status | Scope |
|---------|--------|-------|
| **v0.1** | **MVP implementiert** | compile + query CLI, PDF + Markdown, Claude + Ollama |
| v0.2 | Geplant | Watch-Modus, inkrementelle Compilation |
| v0.3 | Geplant | REST API, Server-Modus, Multi-LLM |
| v0.4 | Geplant | Access Control, Audit Log |
| v0.5 | Geplant | norag-bench Benchmark-Kit |
| v1.0 | Geplant | Stabile CKU-Spezifikation, Production-Ready |

### Lizenz

Apache 2.0 — der komplette Kern ist Open Source. Kein kastrierter Free Tier.

---

## English

### What is noRAG?

noRAG is a **Knowledge Compiler**. Just as a compiler translates source code into machine code, noRAG translates documents into **machine-optimized knowledge**.

The name says it all: **no RAG** — no Retrieval Augmented Generation. Instead, a fundamentally different approach:

**Compile, don't search.**

### The Problem with RAG

RAG (Retrieval Augmented Generation) is the current standard for giving LLMs access to external knowledge. But RAG has structural weaknesses:

- **Pipeline complexity** — Chunking, embedding, vector DB, reranking: too many fragile parts
- **Retrieval quality** — Vector search often finds the wrong thing or loses context
- **Visual knowledge** — Enterprise documents contain diagrams, tables, flowcharts. RAG ignores them completely
- **Context loss** — Chunking destroys the relationship between text, images, and layout

### noRAG's Approach

|  | RAG | noRAG |
|---|---|---|
| **When** | At runtime (every query) | At compile time (once on ingestion) |
| **What** | Search text fragments | Understand document holistically |
| **How** | Vector similarity (fuzzy) | Navigate knowledge structure (exact) |
| **Visuals** | Ignored | First-class citizen |
| **Result** | Raw chunks in prompt | Compiled, minimal knowledge |

### How Does It Work?

```
Document  ──▶  Parser  ──▶  LLM Compiler  ──▶  CKU (YAML)  ──▶  Knowledge Map (SQLite)
                                                                        │
Question  ──▶  Router  ──▶  Assembler  ──▶  LLM  ──▶  Answer   ◀──────┘
```

1. **Compile**: A multimodal LLM reads each document holistically and extracts a **Compiled Knowledge Unit (CKU)** — facts, entities, relations, visual content, summaries
2. **Index**: Entities and facts are indexed in a SQLite knowledge map
3. **Query**: For a question, the knowledge structure is navigated (not searched), minimal context is assembled, and an LLM answers with exact source citations

**No vector store. No embeddings. No chunking. No similarity search.**

### Quickstart

```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY="sk-ant-..."

# Compile documents
norag compile ./documents/

# Ask questions
norag query "How does the onboarding process work in the first week?"
```

### Detailed Testing Guide

See [docs/testing.md](docs/testing.md) for a complete guide with demo scenarios, CLI reference, and explanation of what happens during compile and query.

### Tech Stack

- **Python 3.10+** with Pydantic v2, Typer, Rich
- **CKU format**: YAML files — human-readable, git-versionable
- **Knowledge map**: SQLite with FTS5 full-text search
- **PDF parser**: PyMuPDF (images, tables, diagrams)
- **LLM**: Model-agnostic — Claude API or Ollama (local)

### Roadmap

| Version | Status | Scope |
|---------|--------|-------|
| **v0.1** | **MVP implemented** | compile + query CLI, PDF + Markdown, Claude + Ollama |
| v0.2 | Planned | Watch mode, incremental compilation |
| v0.3 | Planned | REST API, server mode, multi-LLM |
| v0.4 | Planned | Access control, audit log |
| v0.5 | Planned | norag-bench benchmark kit |
| v1.0 | Planned | Stable CKU specification, production-ready |

### License

Apache 2.0 — the entire core is open source. No crippled free tier.
