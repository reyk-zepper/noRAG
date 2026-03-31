# noRAG

> **Compile documents into machine-optimized knowledge. No vectors. No chunks. No embeddings. Just understanding.**

**[Deutsch](#deutsch)** | **[English](#english)**

---

## English

### What is noRAG?

noRAG is a **Knowledge Compiler**. Just as a compiler translates source code into machine code, noRAG translates documents into **machine-optimized knowledge**.

The name says it all: **no RAG** — no Retrieval Augmented Generation. Instead, a fundamentally different approach:

**Compile, don't search.**

### The Problem with RAG

RAG (Retrieval Augmented Generation) is the current standard for giving LLMs access to external knowledge. But RAG has structural weaknesses:

- **Pipeline complexity** — Chunking, embedding, vector DB, reranking: too many fragile moving parts
- **Retrieval quality** — Vector similarity is fuzzy by nature. It often finds the wrong thing or loses context across chunk boundaries
- **Visual knowledge** — Enterprise documents are full of diagrams, tables, and flowcharts. RAG ignores them completely
- **Context loss** — Chunking destroys the relationship between text, images, and layout. A chart on page 3 that explains the table on page 4 is lost

noRAG doesn't try to build a better RAG pipeline. It eliminates the need for one entirely.

### How noRAG Works

```
Document  ──▶  Parser  ──▶  LLM Compiler  ──▶  CKU (YAML)  ──▶  Knowledge Map (SQLite)
                                                                        |
Question  ──▶  Router  ──▶  Assembler  ──▶  LLM  ──▶  Answer   <──────┘
```

**Phase 1 — Compile (once per document)**

A multimodal LLM reads each document holistically and extracts a **Compiled Knowledge Unit (CKU)**: facts, entities, relationships, visual content descriptions, and summaries. The CKU is stored as a human-readable YAML file and indexed in a SQLite knowledge map.

**Phase 2 — Query (per question)**

When a question is asked, the knowledge map is navigated (not searched via vectors) to find relevant CKUs. Minimal, precise context is assembled from the compiled knowledge, and an LLM answers with exact source citations.

**No vector store. No embeddings. No chunking. No similarity search.**

|  | RAG | noRAG |
|---|---|---|
| **When** | At runtime (every query) | At compile time (once on ingestion) |
| **What** | Search text fragments | Understand document holistically |
| **How** | Vector similarity (fuzzy) | Navigate knowledge structure (exact) |
| **Visuals** | Ignored | First-class citizen |
| **Result** | Raw chunks in prompt | Compiled, minimal knowledge |
| **Cost per query** | ~2000-4000 tokens context | ~200-500 tokens context |

### Installation

**Requirements:** Python 3.10+

```bash
# Clone the repository
git clone https://github.com/reyk-zepper/noRAG.git
cd noRAG

# Install with Claude API support
pip install -e ".[claude]"

# Or install with all optional dependencies
pip install -e ".[claude,ollama,dev]"
```

**With uv (recommended):**

```bash
uv sync --extra dev
```

### Configuration

noRAG is configured through environment variables, a config file, or CLI flags.

**Environment variables** (highest priority):

```bash
# LLM Provider
export NORAG_PROVIDER=ollama          # or "claude"
export NORAG_MODEL=qwen2.5:7b        # any model your provider supports
export NORAG_OLLAMA_HOST=http://localhost:11434

# For Claude API
export ANTHROPIC_API_KEY=sk-ant-...

# Optional
export NORAG_MAX_SECTION_LINES=200    # document splitting threshold
```

**Config file** (`.norag/config.yaml`):

```yaml
provider: ollama
model: qwen2.5:7b
ollama_host: http://localhost:11434
max_section_lines: 200
```

**Priority:** CLI flags > environment variables > config file > defaults.

### Quickstart

```bash
# 1. Compile your documents
norag compile ./documents/

# 2. Ask questions
norag query "How does the onboarding process work?"

# 3. Watch for changes (auto-recompile)
norag watch ./documents/

# 4. Start the REST API
norag serve
```

### CLI Reference

| Command | Description |
|---------|-------------|
| `norag compile <path>` | Compile documents into CKUs (PDF, Markdown) |
| `norag query "question?"` | Query compiled knowledge |
| `norag watch <dir>` | Watch directory, auto-recompile on changes |
| `norag serve` | Start REST API server (default: http://localhost:8484) |
| `norag audit` | Show the audit log |
| `norag bench <dataset>` | Run a benchmark against a dataset |
| `norag info` | Show store status, configuration, and stats |
| `norag validate` | Validate CKU files against the schema |
| `norag --version` | Show version |

**Common flags** (available on most commands):

```bash
--provider, -p    LLM provider (claude | ollama)
--model, -m       Model name
--store, -s       Store directory (default: .norag)
--verbose, -v     Show detailed output
```

**Compile options:**

```bash
norag compile docs/ --force              # recompile even if up-to-date
norag compile docs/ --roles hr,management  # set access control roles
```

**Serve options:**

```bash
norag serve --host 0.0.0.0 --port 8484 --reload
```

### REST API

Start the server with `norag serve` and open http://localhost:8484/docs for interactive OpenAPI documentation.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (provider, model, version) |
| `/knowledge` | GET | List all CKUs with stats |
| `/compile` | POST | Compile a document (multipart file upload) |
| `/query` | POST | Query knowledge (`{"question": "...", "user_role": "..."}`) |
| `/audit` | GET | Browse audit log events |
| `/docs` | GET | Interactive OpenAPI documentation |

**Example — compile via API:**

```bash
curl -X POST http://localhost:8484/compile \
  -F "file=@document.pdf" \
  -F "roles=engineering"
```

**Example — query via API:**

```bash
curl -X POST http://localhost:8484/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is our deployment process?", "user_role": "engineering"}'
```

### Features

#### Document Splitting

Large documents are automatically split into sections before LLM compilation. Markdown files are split at H1/H2 headings, PDFs by page groups. Each section is compiled independently and the results are merged into a single CKU with deduplicated entities and combined facts.

This makes noRAG work reliably even with small local models (7B parameters) on large documents.

#### Watch Mode

`norag watch ./docs/` monitors a directory for file changes and automatically recompiles modified documents. Uses `watchfiles` (Rust-based) with configurable debounce. Only changed files are recompiled thanks to hash-based change detection.

#### Access Control

CKUs support role-based access control. When compiling, assign roles:

```bash
norag compile confidential.pdf --roles hr,management
```

When querying, pass the user's role. CKUs without matching roles are invisible:

```bash
curl -X POST http://localhost:8484/query \
  -d '{"question": "What are the salary bands?", "user_role": "hr"}'
```

CKUs with no roles assigned are public (visible to everyone).

#### Audit Log

Every compilation and query is logged automatically in a SQLite audit log. View it with:

```bash
norag audit                    # last 20 events
norag audit --type query -n 50 # last 50 query events
```

Or via the API: `GET /audit?event_type=query&limit=50`

#### Benchmark Kit

norag-bench measures the quality of your knowledge compilation:

```bash
norag bench benchmarks/sample --provider ollama --model qwen2.5:7b -o report.json
```

Metrics: keyword match score, query latency, token efficiency, compile time. Includes a sample dataset for testing.

#### CKU Specification v1

The CKU format is a formal, open specification. See [docs/cku-spec-v1.md](docs/cku-spec-v1.md) for the full schema, field definitions, constraints, and examples. CKUs are YAML files that are human-readable, git-versionable, and tool-friendly.

### Architecture & Design Decisions

#### Why YAML for CKUs, not JSON or a database?

CKUs are stored as YAML files because they are meant to be **auditable**. You should be able to open a CKU, read it, understand it, and verify it. YAML is human-readable, git-diffable, and can be reviewed in code review. The SQLite knowledge map provides fast lookup — the YAML files are the source of truth.

#### Why SQLite for the Knowledge Map?

SQLite is zero-config, embedded, and supports FTS5 full-text search. No external database server needed. The knowledge map is derived from CKUs and can be rebuilt at any time. This keeps noRAG self-contained — a single directory (`.norag/`) contains everything.

#### Why compile-time instead of runtime?

The key insight: **understanding a document is expensive, but it only needs to happen once.** RAG pays the retrieval cost on every query. noRAG pays the compilation cost once and amortizes it across all queries. This also means the compiled knowledge can be reviewed, corrected, and versioned — something impossible with vector embeddings.

#### Why model-agnostic?

noRAG works with any LLM that can output structured JSON: Claude, GPT, Llama, Qwen, Mistral, or any Ollama-compatible model. The compilation quality scales with model capability, but even 7B local models produce usable CKUs thanks to document splitting. No vendor lock-in.

#### Why no embeddings?

Embeddings are a lossy compression of meaning. They trade precision for speed — but the speed advantage disappears when you compile knowledge ahead of time. CKUs preserve the full structure: entities, relationships, facts with confidence scores, visual content descriptions. This enables exact navigation instead of approximate search.

### Project Structure

```
noRAG/
├── src/norag/
│   ├── cli/            # CLI commands (compile, query, watch, serve, audit, bench, info, validate)
│   ├── compiler/       # Parsers (PDF, Markdown), LLM providers, splitter, merger
│   ├── models/         # CKU Pydantic models
│   ├── query/          # Router, assembler, query engine
│   ├── store/          # CKU filesystem store, SQLite knowledge map, audit log
│   ├── server/         # FastAPI REST API
│   └── bench/          # Benchmark kit (dataset, runner, metrics, report)
├── tests/              # 319 unit tests
├── benchmarks/         # Sample benchmark dataset
├── docs/               # CKU Spec v1, design documents, testing guide
└── .norag/             # Local knowledge store (created on first compile)
```

### Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.10+ | Ecosystem, LLM libraries, accessibility |
| Models | Pydantic v2 | Strict validation, YAML serialization |
| CLI | Typer + Rich | Type-safe CLI with beautiful output |
| API | FastAPI + Uvicorn | Async, auto-generated OpenAPI docs |
| PDF Parser | PyMuPDF | Tables, images, diagrams extraction |
| Knowledge Map | SQLite + FTS5 | Zero-config, full-text search |
| File Watcher | watchfiles | Rust-based, fast, low CPU usage |
| LLM (Cloud) | Claude API | Best structured output quality |
| LLM (Local) | Ollama | Any model, completely offline |

### Differentiation

noRAG is not a better RAG framework. It is a different paradigm.

| | RAG Frameworks | GraphRAG | Large Context Windows | Fine-Tuning | **noRAG** |
|---|---|---|---|---|---|
| Approach | Optimize retrieval | Add graph layer to RAG | Brute-force everything into context | Bake knowledge into weights | **Compile knowledge ahead of time** |
| Embeddings | Yes | Yes | No | No | **No** |
| Vector DB | Yes | Yes | No | No | **No** |
| Chunking | Yes | Yes | No | No | **No** |
| Visual content | Ignored | Ignored | Partial | No | **First-class** |
| Auditable | No | Partially | No | No | **Yes (CKU is readable)** |
| Model-agnostic | Partially | No | No | No | **Yes** |
| Update speed | Minutes | Hours | Instant | Hours/days | **Seconds/minutes** |
| Cost per query | High (retrieval + LLM) | High | Very high | Low | **Low** |

### Roadmap

| Version | Status | What was delivered |
|---------|--------|-------------------|
| v0.1 | Done | Core compile + query CLI, PDF + Markdown parsers, Claude + Ollama providers |
| v0.2 | Done | Document splitting (heading-aware + page-based), watch mode, incremental compilation |
| v0.3 | Done | FastAPI REST API with OpenAPI docs, server mode |
| v0.4 | Done | Role-based access control on CKU level, SQLite audit log |
| v0.5 | Done | norag-bench benchmark kit with dataset format, metrics, reports |
| **v1.0** | **Done** | **CKU Specification v1, schema validation, info command, production-ready** |

### Running Tests

```bash
# Run all 319 tests
uv run pytest tests/ -v

# Run specific test module
uv run pytest tests/test_splitter.py -v

# Run with coverage
uv run pytest tests/ --cov=norag
```

### License

Apache 2.0 — the entire core is open source. No crippled free tier, no proprietary extensions required for production use.

---

## Deutsch

### Was ist noRAG?

noRAG ist ein **Knowledge Compiler**. So wie ein Compiler Quellcode in Maschinencode uebersetzt, uebersetzt noRAG Dokumente in **maschinenoptimiertes Wissen**.

Der Name sagt es: **no RAG** — kein Retrieval Augmented Generation. Stattdessen ein fundamental anderer Ansatz:

**Compile, don't search.**

### Das Problem mit RAG

RAG (Retrieval Augmented Generation) ist der aktuelle Standard, um LLMs Zugriff auf externes Wissen zu geben. Aber RAG hat strukturelle Schwaechen:

- **Pipeline-Komplexitaet** — Chunking, Embedding, Vector DB, Reranking: zu viele fragile Teile
- **Retrieval-Qualitaet** — Vektoraehnlichkeit ist von Natur aus unscharf. Findet oft das Falsche oder verliert den Kontext an Chunk-Grenzen
- **Visuelles Wissen** — Enterprise-Dokumente sind voll mit Diagrammen, Tabellen, Flowcharts. RAG ignoriert diese komplett
- **Kontextverlust** — Chunking zerstoert den Zusammenhang. Ein Chart auf Seite 3, der die Tabelle auf Seite 4 erklaert, geht verloren

noRAG versucht nicht, eine bessere RAG-Pipeline zu bauen. Es eliminiert die Notwendigkeit dafuer.

### Wie noRAG funktioniert

```
Dokument  ──▶  Parser  ──▶  LLM Compiler  ──▶  CKU (YAML)  ──▶  Knowledge Map (SQLite)
                                                                        |
Frage     ──▶  Router  ──▶  Assembler  ──▶  LLM  ──▶  Antwort  <──────┘
```

**Phase 1 — Compile (einmal pro Dokument)**

Ein multimodales LLM liest jedes Dokument holistisch und extrahiert eine **Compiled Knowledge Unit (CKU)**: Fakten, Entitaeten, Beziehungen, visuelle Inhalte, Zusammenfassungen. Die CKU wird als human-readable YAML-Datei gespeichert und in einer SQLite-Wissenskarte indiziert.

**Phase 2 — Query (pro Frage)**

Bei einer Frage wird die Wissenskarte navigiert (nicht per Vektor durchsucht), um relevante CKUs zu finden. Minimaler, praeziser Kontext wird aus dem kompilierten Wissen assembliert, und ein LLM antwortet mit exakten Quellenangaben.

**Kein Vector Store. Keine Embeddings. Kein Chunking. Keine Similarity Search.**

|  | RAG | noRAG |
|---|---|---|
| **Wann** | Zur Laufzeit (bei jeder Frage) | Zur Compile-Zeit (einmal bei Aufnahme) |
| **Was** | Textfragmente suchen | Dokument holistisch verstehen |
| **Wie** | Vektoraehnlichkeit (fuzzy) | Wissensstruktur navigieren (exakt) |
| **Visuelles** | Wird ignoriert | First-Class-Citizen |
| **Ergebnis** | Rohe Chunks im Prompt | Kompiliertes, minimales Wissen |
| **Kosten pro Query** | ~2000-4000 Tokens Kontext | ~200-500 Tokens Kontext |

### Installation

**Voraussetzungen:** Python 3.10+

```bash
# Repository klonen
git clone https://github.com/reyk-zepper/noRAG.git
cd noRAG

# Mit Claude API-Unterstuetzung installieren
pip install -e ".[claude]"

# Oder mit allen optionalen Abhaengigkeiten
pip install -e ".[claude,ollama,dev]"
```

**Mit uv (empfohlen):**

```bash
uv sync --extra dev
```

### Konfiguration

noRAG wird ueber Umgebungsvariablen, eine Config-Datei oder CLI-Flags konfiguriert.

**Umgebungsvariablen** (hoechste Prioritaet):

```bash
# LLM Provider
export NORAG_PROVIDER=ollama          # oder "claude"
export NORAG_MODEL=qwen2.5:7b        # jedes Modell, das Ihr Provider unterstuetzt
export NORAG_OLLAMA_HOST=http://localhost:11434

# Fuer Claude API
export ANTHROPIC_API_KEY=sk-ant-...

# Optional
export NORAG_MAX_SECTION_LINES=200    # Schwellwert fuer Document Splitting
```

**Config-Datei** (`.norag/config.yaml`):

```yaml
provider: ollama
model: qwen2.5:7b
ollama_host: http://localhost:11434
max_section_lines: 200
```

**Prioritaet:** CLI-Flags > Umgebungsvariablen > Config-Datei > Defaults.

### Schnellstart

```bash
# 1. Dokumente kompilieren
norag compile ./documents/

# 2. Fragen stellen
norag query "Wie laeuft das Onboarding in der ersten Woche?"

# 3. Aenderungen beobachten (auto-recompile)
norag watch ./documents/

# 4. REST API starten
norag serve
```

### CLI-Referenz

| Befehl | Beschreibung |
|--------|-------------|
| `norag compile <pfad>` | Dokumente in CKUs kompilieren (PDF, Markdown) |
| `norag query "Frage?"` | Kompiliertes Wissen abfragen |
| `norag watch <verz>` | Verzeichnis beobachten, automatisch rekompilieren |
| `norag serve` | REST API-Server starten (Standard: http://localhost:8484) |
| `norag audit` | Audit-Log anzeigen |
| `norag bench <dataset>` | Benchmark gegen ein Dataset ausfuehren |
| `norag info` | Store-Status, Konfiguration und Statistiken |
| `norag validate` | CKU-Dateien gegen das Schema validieren |
| `norag --version` | Version anzeigen |

**Compile-Optionen:**

```bash
norag compile docs/ --force                   # auch wenn aktuell, neu kompilieren
norag compile docs/ --roles hr,management     # Zugriffskontroll-Rollen setzen
```

### REST API

Server starten mit `norag serve` und http://localhost:8484/docs fuer die interaktive OpenAPI-Dokumentation oeffnen.

| Endpunkt | Methode | Beschreibung |
|----------|---------|-------------|
| `/health` | GET | Health Check (Provider, Model, Version) |
| `/knowledge` | GET | Alle CKUs mit Statistiken auflisten |
| `/compile` | POST | Dokument kompilieren (Multipart File Upload) |
| `/query` | POST | Wissen abfragen (`{"question": "...", "user_role": "..."}`) |
| `/audit` | GET | Audit-Log Events durchsuchen |
| `/docs` | GET | Interaktive OpenAPI-Dokumentation |

### Features

#### Document Splitting

Grosse Dokumente werden vor der LLM-Kompilation automatisch in Sektionen gesplittet. Markdown-Dateien an H1/H2-Headings, PDFs nach Seitengruppen. Jede Sektion wird unabhaengig kompiliert und die Ergebnisse in eine einzelne CKU mit deduplizierten Entitaeten und zusammengefuehrten Fakten gemerged.

Das macht noRAG zuverlaessig nutzbar auch mit kleinen lokalen Modellen (7B Parameter) auf grossen Dokumenten.

#### Watch-Modus

`norag watch ./docs/` ueberwacht ein Verzeichnis auf Dateiänderungen und rekompiliert geaenderte Dokumente automatisch. Nutzt `watchfiles` (Rust-basiert) mit konfigurierbarem Debounce. Nur geaenderte Dateien werden dank Hash-basierter Aenderungserkennung rekompiliert.

#### Zugriffskontrolle

CKUs unterstuetzen rollenbasierte Zugriffskontrolle. Beim Kompilieren Rollen zuweisen:

```bash
norag compile vertraulich.pdf --roles hr,management
```

Beim Abfragen die Rolle des Users angeben. CKUs ohne passende Rollen sind unsichtbar:

```bash
curl -X POST http://localhost:8484/query \
  -d '{"question": "Wie sind die Gehaltsbaender?", "user_role": "hr"}'
```

CKUs ohne zugewiesene Rollen sind oeffentlich (fuer alle sichtbar).

#### Audit Log

Jede Kompilation und Query wird automatisch in einem SQLite-Audit-Log protokolliert:

```bash
norag audit                    # letzte 20 Events
norag audit --type query -n 50 # letzte 50 Query-Events
```

#### Benchmark-Kit

norag-bench misst die Qualitaet der Wissenskompilation:

```bash
norag bench benchmarks/sample --provider ollama --model qwen2.5:7b -o report.json
```

Metriken: Keyword-Match-Score, Query-Latenz, Token-Effizienz, Compile-Zeit.

#### CKU-Spezifikation v1

Das CKU-Format ist eine formale, offene Spezifikation. Siehe [docs/cku-spec-v1.md](docs/cku-spec-v1.md) fuer das vollstaendige Schema, Felddefinitionen, Constraints und Beispiele. CKUs sind YAML-Dateien — human-readable, git-versionierbar, tool-freundlich.

### Architektur-Entscheidungen

#### Warum YAML fuer CKUs und nicht JSON oder eine Datenbank?

CKUs werden als YAML gespeichert, weil sie **auditierbar** sein sollen. Man soll eine CKU oeffnen, lesen, verstehen und ueberpruefen koennen. YAML ist human-readable, git-diffbar und kann im Code Review geprueft werden. Die SQLite-Wissenskarte bietet schnelles Lookup — die YAML-Dateien sind die Source of Truth.

#### Warum SQLite fuer die Knowledge Map?

SQLite ist Zero-Config, embedded und unterstuetzt FTS5-Volltextsuche. Kein externer Datenbankserver noetig. Die Knowledge Map wird aus CKUs abgeleitet und kann jederzeit neu aufgebaut werden. Das haelt noRAG in sich abgeschlossen — ein einzelnes Verzeichnis (`.norag/`) enthaelt alles.

#### Warum Compile-Zeit statt Laufzeit?

Das Kern-Insight: **Ein Dokument zu verstehen ist teuer, muss aber nur einmal passieren.** RAG zahlt die Retrieval-Kosten bei jeder Query. noRAG zahlt die Kompilationskosten einmal und amortisiert sie ueber alle Queries. Ausserdem kann das kompilierte Wissen reviewed, korrigiert und versioniert werden — etwas das mit Vektor-Embeddings unmoeglich ist.

#### Warum model-agnostisch?

noRAG funktioniert mit jedem LLM, das strukturiertes JSON ausgeben kann: Claude, GPT, Llama, Qwen, Mistral oder jedes Ollama-kompatible Modell. Die Kompilationsqualitaet skaliert mit der Modellfaehigkeit, aber selbst 7B-Modelle erzeugen dank Document Splitting brauchbare CKUs. Kein Vendor-Lock-in.

#### Warum keine Embeddings?

Embeddings sind eine verlustbehaftete Komprimierung von Bedeutung. Sie tauschen Praezision gegen Geschwindigkeit — aber der Geschwindigkeitsvorteil verschwindet, wenn man Wissen vorher kompiliert. CKUs bewahren die volle Struktur: Entitaeten, Beziehungen, Fakten mit Confidence-Scores, visuelle Inhalte. Das ermoeglicht exakte Navigation statt approximativer Suche.

### Differenzierung

noRAG ist kein besseres RAG-Framework. Es ist ein anderes Paradigma.

| | RAG-Frameworks | GraphRAG | Grosse Context Windows | Fine-Tuning | **noRAG** |
|---|---|---|---|---|---|
| Ansatz | Retrieval optimieren | Graph-Layer auf RAG | Alles in den Kontext | Wissen in Weights | **Wissen vorab kompilieren** |
| Embeddings | Ja | Ja | Nein | Nein | **Nein** |
| Vector DB | Ja | Ja | Nein | Nein | **Nein** |
| Chunking | Ja | Ja | Nein | Nein | **Nein** |
| Visuelle Inhalte | Ignoriert | Ignoriert | Teilweise | Nein | **First-Class** |
| Auditierbar | Nein | Teilweise | Nein | Nein | **Ja (CKU ist lesbar)** |
| Model-agnostisch | Teilweise | Nein | Nein | Nein | **Ja** |
| Update-Speed | Minuten | Stunden | Sofort | Stunden/Tage | **Sekunden/Minuten** |

### Tech Stack

| Komponente | Technologie | Warum |
|------------|-----------|-------|
| Sprache | Python 3.10+ | Oekosystem, LLM-Bibliotheken, Zugaenglichkeit |
| Modelle | Pydantic v2 | Strikte Validierung, YAML-Serialisierung |
| CLI | Typer + Rich | Typsicheres CLI mit schoener Ausgabe |
| API | FastAPI + Uvicorn | Async, auto-generierte OpenAPI-Docs |
| PDF-Parser | PyMuPDF | Tabellen, Bilder, Diagramme |
| Knowledge Map | SQLite + FTS5 | Zero-Config, Volltextsuche |
| File Watcher | watchfiles | Rust-basiert, schnell, niedriger CPU-Verbrauch |
| LLM (Cloud) | Claude API | Beste Qualitaet fuer strukturierten Output |
| LLM (Lokal) | Ollama | Jedes Modell, komplett offline |

### Projektstruktur

```
noRAG/
├── src/norag/
│   ├── cli/            # CLI-Befehle (compile, query, watch, serve, audit, bench, info, validate)
│   ├── compiler/       # Parser (PDF, Markdown), LLM-Provider, Splitter, Merger
│   ├── models/         # CKU Pydantic-Modelle
│   ├── query/          # Router, Assembler, Query Engine
│   ├── store/          # CKU-Filesystem-Store, SQLite Knowledge Map, Audit Log
│   ├── server/         # FastAPI REST API
│   └── bench/          # Benchmark-Kit (Dataset, Runner, Metrics, Report)
├── tests/              # 319 Unit-Tests
├── benchmarks/         # Beispiel-Benchmark-Dataset
├── docs/               # CKU Spec v1, Design-Dokumente, Test-Anleitung
└── .norag/             # Lokaler Knowledge Store (wird beim ersten Compile erstellt)
```

### Roadmap

| Version | Status | Was wurde geliefert |
|---------|--------|---------------------|
| v0.1 | Fertig | Kern-Compile + Query CLI, PDF + Markdown-Parser, Claude + Ollama-Provider |
| v0.2 | Fertig | Document Splitting (Heading-aware + Seiten-basiert), Watch-Modus, inkrementelle Kompilation |
| v0.3 | Fertig | FastAPI REST API mit OpenAPI-Docs, Server-Modus |
| v0.4 | Fertig | Rollenbasierte Zugriffskontrolle auf CKU-Ebene, SQLite Audit Log |
| v0.5 | Fertig | norag-bench Benchmark-Kit mit Dataset-Format, Metriken, Reports |
| **v1.0** | **Fertig** | **CKU-Spezifikation v1, Schema-Validierung, Info-Command, Production-Ready** |

### Tests ausfuehren

```bash
# Alle 319 Tests ausfuehren
uv run pytest tests/ -v

# Spezifisches Testmodul
uv run pytest tests/test_splitter.py -v
```

### Lizenz

Apache 2.0 — der komplette Kern ist Open Source. Kein kastrierter Free Tier, keine proprietaeren Erweiterungen fuer den produktiven Einsatz noetig.
