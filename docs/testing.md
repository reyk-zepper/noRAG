# noRAG — Test & Demo Guide

## Voraussetzungen

- Python >= 3.10
- Ein LLM-Provider: Claude API Key **oder** lokale Ollama-Installation

## Installation

```bash
cd /path/to/noRAG

# Mit Claude-Support
pip install -e ".[claude]"

# Mit Ollama-Support
pip install -e ".[ollama]"

# Alles (inkl. Dev-Tools)
pip install -e ".[claude,ollama,dev]"
```

## Schnelltest (ohne LLM)

Pruefen ob Installation und Imports funktionieren:

```bash
# CLI verfuegbar?
norag --help

# Python-Imports ok?
python -c "from norag.models.cku import CKU; print('Models OK')"
python -c "from norag.compiler.engine import CompilerEngine; print('Compiler OK')"
python -c "from norag.query.engine import QueryEngine; print('Query OK')"
```

## Demo: noRAG kompiliert seine eigene Doku

Das Design-Dokument (`docs/plans/2026-03-16-norag-design.md`) eignet sich ideal
als erstes Testdokument — noRAG erklaert sich selbst.

### Mit Claude

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# Dokument kompilieren
norag compile docs/

# Erwartete Ausgabe:
# ✓ Compiled: 1 document(s)
# Total: 1 | Compiled: 1 | Skipped: 0 | Failed: 0

# Fragen stellen
norag query "Was ist der Unterschied zwischen noRAG und RAG?"
norag query "Wie funktioniert die CKU-Spezifikation?"
norag query "Welche Benchmark-Dimensionen gibt es?" --stats
norag query "What is the compile pipeline?" --stats
```

### Mit Ollama (lokal)

```bash
# Ollama muss laufen (z.B. mit llama3.1)
ollama serve &
ollama pull llama3.1

# Kompilieren mit Ollama
norag compile docs/ --provider ollama --model llama3.1

# Fragen
norag query "Was ist noRAG?" --provider ollama --model llama3.1
```

## Was passiert bei der Demo?

### Compile-Phase

1. **Parse**: Das Markdown-Dokument wird gelesen und in strukturierte Seiten zerlegt
2. **LLM Compile**: Das LLM liest das Dokument holistisch und extrahiert:
   - Zusammenfassungen (document + sections)
   - Entitaeten (Konzepte, Systeme, Prozesse)
   - Fakten (diskrete Aussagen mit Quellenangabe)
   - Visuelle Inhalte (Tabellen, Diagramme)
3. **Store**: Die CKU wird als YAML-Datei in `.norag/ckus/` gespeichert
4. **Index**: Entitaeten, Fakten und Topics werden in SQLite FTS5 indiziert

### Query-Phase

1. **Route**: Keywords aus der Frage → Entity/Topic/FTS-Lookup in SQLite
2. **Assemble**: Relevante Fakten, Summaries, Visuals aus CKUs extrahieren
3. **Answer**: Minimaler Kontext + Frage → LLM → Antwort mit Quellenangabe

## Erwartete Dateien nach Compile

```
.norag/
├── ckus/
│   └── 2026-03-16-norag-design-XXXXXXXX.yaml   # Compiled Knowledge Unit
└── knowledge.db                                  # SQLite Knowledge Map
```

## CLI-Referenz

```bash
# Compile
norag compile <pfad>              # Datei oder Verzeichnis
norag compile <pfad> --force      # Erneut kompilieren, auch wenn aktuell
norag compile <pfad> -p ollama    # Anderer Provider
norag compile <pfad> -m llama3.1  # Anderes Modell
norag compile <pfad> -v           # Verbose-Ausgabe

# Query
norag query "Frage"               # Frage stellen
norag query "Frage" --stats       # Mit Statistiken (CKUs, Tokens, Provider)
norag query "Frage" --no-sources  # Ohne Quellenangaben
norag query "Frage" -k 3          # Max. 3 CKUs im Kontext
norag query "Frage" -p ollama     # Anderer Provider
```
