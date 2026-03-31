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

### CLI-Referenz

```bash
norag compile <path>     # Dokumente kompilieren (PDF, Markdown)
norag query "Frage?"     # Wissen abfragen
norag watch <dir>        # Verzeichnis beobachten, auto-recompile
norag serve              # REST API starten (http://localhost:8484/docs)
norag audit              # Audit-Log anzeigen
norag bench <dataset>    # Benchmark ausfuehren
norag info               # Store-Status und Konfiguration
norag validate           # CKU-Dateien validieren
norag --version          # Version anzeigen
```

### REST API

```bash
norag serve --port 8484
```

| Endpunkt          | Methode | Beschreibung |
|-------------------|---------|--------------|
| `/health`         | GET     | Health Check |
| `/knowledge`      | GET     | CKU-Uebersicht und Stats |
| `/compile`        | POST    | Dokument kompilieren (File Upload) |
| `/query`          | POST    | Wissen abfragen |
| `/audit`          | GET     | Audit-Log Events |
| `/docs`           | GET     | OpenAPI Dokumentation |

### Features

- **Document Splitting** — Grosse Dokumente werden automatisch an H1/H2-Headings gesplittet
- **Watch-Modus** — Automatische Rekompilation bei Dateiänderungen
- **Access Control** — Rollenbasierte Zugriffskontrolle auf CKU-Ebene
- **Audit Log** — Jede Kompilation und Query wird geloggt
- **Benchmark-Kit** — Messbare Qualitaetsmetriken (Keyword-Score, Latenz, Token-Effizienz)
- **CKU Spec v1** — Formale, offene Spezifikation ([docs/cku-spec-v1.md](docs/cku-spec-v1.md))

### Tech Stack

- **Python 3.10+** mit Pydantic v2, Typer, Rich, FastAPI
- **CKU-Format**: YAML-Dateien — human-readable, git-versionierbar
- **Knowledge Map**: SQLite mit FTS5 Volltext-Suche
- **PDF-Parser**: PyMuPDF (Bilder, Tabellen, Diagramme)
- **LLM**: Model-agnostisch — Claude API oder Ollama (lokal)
- **API**: FastAPI mit OpenAPI-Docs

### Roadmap

| Version | Status | Scope |
|---------|--------|-------|
| v0.1 | ✓ | compile + query CLI, PDF + Markdown, Claude + Ollama |
| v0.2 | ✓ | Document Splitting, Watch-Modus |
| v0.3 | ✓ | REST API (FastAPI), Server-Modus |
| v0.4 | ✓ | Access Control, Audit Log |
| v0.5 | ✓ | norag-bench Benchmark-Kit |
| **v1.0** | **✓** | **Stabile CKU-Spezifikation, Production-Ready** |

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

### CLI Reference

```bash
norag compile <path>     # Compile documents (PDF, Markdown)
norag query "question?"  # Query compiled knowledge
norag watch <dir>        # Watch directory, auto-recompile on changes
norag serve              # Start REST API (http://localhost:8484/docs)
norag audit              # Show audit log
norag bench <dataset>    # Run benchmark
norag info               # Show store status and configuration
norag validate           # Validate CKU files against schema
norag --version          # Show version
```

### REST API

```bash
norag serve --port 8484
```

| Endpoint           | Method | Description |
|--------------------|--------|-------------|
| `/health`          | GET    | Health check |
| `/knowledge`       | GET    | CKU overview and stats |
| `/compile`         | POST   | Compile document (file upload) |
| `/query`           | POST   | Query compiled knowledge |
| `/audit`           | GET    | Audit log events |
| `/docs`            | GET    | OpenAPI documentation |

### Features

- **Document Splitting** — Large documents are automatically split at H1/H2 headings
- **Watch Mode** — Automatic recompilation on file changes
- **Access Control** — Role-based access control at CKU level
- **Audit Log** — Every compilation and query is logged
- **Benchmark Kit** — Measurable quality metrics (keyword score, latency, token efficiency)
- **CKU Spec v1** — Formal, open specification ([docs/cku-spec-v1.md](docs/cku-spec-v1.md))

### Tech Stack

- **Python 3.10+** with Pydantic v2, Typer, Rich, FastAPI
- **CKU format**: YAML files — human-readable, git-versionable
- **Knowledge map**: SQLite with FTS5 full-text search
- **PDF parser**: PyMuPDF (images, tables, diagrams)
- **LLM**: Model-agnostic — Claude API or Ollama (local)
- **API**: FastAPI with OpenAPI docs

### Roadmap

| Version | Status | Scope |
|---------|--------|-------|
| v0.1 | ✓ | compile + query CLI, PDF + Markdown, Claude + Ollama |
| v0.2 | ✓ | Document Splitting, watch mode |
| v0.3 | ✓ | REST API (FastAPI), server mode |
| v0.4 | ✓ | Access control, audit log |
| v0.5 | ✓ | norag-bench benchmark kit |
| **v1.0** | **✓** | **Stable CKU specification, production-ready** |

### License

Apache 2.0 — the entire core is open source. No crippled free tier.
