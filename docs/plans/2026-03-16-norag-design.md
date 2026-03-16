# noRAG — Design Document

> *noRAG compiles documents into machine-optimized knowledge. No vectors. No chunks. No embeddings. Just understanding.*

**Datum:** 2026-03-16
**Status:** Konzeptphase
**Autor:** Brainstorming-Session

---

## Inhaltsverzeichnis

1. [Kernkonzept](#1-kernkonzept)
2. [Inkrementelle Compilation Pipeline](#2-inkrementelle-compilation-pipeline)
3. [CKU — Compiled Knowledge Unit](#3-cku--compiled-knowledge-unit)
4. [Query Engine](#4-query-engine)
5. [Architektur & Tech Stack](#5-architektur--tech-stack)
6. [Enterprise Features](#6-enterprise-features)
7. [Open Source Strategie & USP](#7-open-source-strategie--usp)
8. [MVP-Scope](#8-mvp-scope)
9. [Differenzierung](#9-differenzierung)
10. [Validierung & Benchmarks](#10-validierung--benchmarks)

---

## 1. Kernkonzept

**"Compile, don't search."**

noRAG ist ein **Knowledge Compiler**. So wie ein Compiler Quellcode in Maschinencode uebersetzt, uebersetzt noRAG Dokumente in **maschinenoptimiertes Wissen**.

### Das Problem mit RAG

RAG (Retrieval Augmented Generation) ist der aktuelle Standard, um LLMs Zugriff auf externes Wissen zu geben. Aber RAG hat strukturelle Schwaechen:

- **Pipeline-Komplexitaet**: Chunking, Embedding, Vector DB, Reranking — zu viele fragile Teile
- **Retrieval-Qualitaet**: Vektorsuche findet oft das Falsche oder verliert Kontext
- **Architektur-Problem**: "Suchen und ins Prompt stopfen" ist ein Workaround, keine echte Loesung
- **Visuelles Wissen**: Enterprise-Dokumente enthalten Diagramme, Flowcharts, Tabellen — RAG ignoriert diese komplett
- **Kontextverlust**: Chunking zerstoert den Zusammenhang zwischen Text, Bildern und Layout

### noRAGs Ansatz

| | RAG | noRAG |
|---|---|---|
| **Wann** | Zur Laufzeit (bei jeder Frage) | Zur Compile-Zeit (einmal bei Aufnahme) |
| **Was** | Textfragmente suchen | Dokument verstehen |
| **Wie** | Vektoraehnlichkeit (fuzzy) | Wissensstruktur navigieren (exakt) |
| **Visuelles** | Wird ignoriert oder zu Text geflacht | Wird als Wissen erster Klasse behandelt |
| **Ergebnis** | Rohe Chunks im Prompt | Kompiliertes, minimales Wissen im Prompt |

### Der Prozess

> Ein multimodales LLM liest jedes Dokument **holistisch** — Text, Bilder, Tabellen, Layout, Querverweise — und extrahiert daraus eine strukturierte **Compiled Knowledge Unit (CKU)**, die das Zusammenspiel aller Elemente erhaelt.

Eine CKU ist kein Textauszug. Es ist **Verstaendnis in strukturierter Form**: Fakten mit Quellverweis, Entitaeten mit Beziehungen, visuelle Inhalte als beschriebene Prozesse, und hierarchische Zusammenfassungen auf mehreren Detailstufen.

**Kein Vector Store. Keine Embeddings. Kein Chunking. Keine Similarity Search.**

---

## 2. Inkrementelle Compilation Pipeline

Der Knowledge Compiler laeuft nicht nur einmal — er haelt das Wissen **stetig aktuell**. Neue Dokumente fliessen innerhalb von Sekunden bis Minuten ins System ein.

### Build-System-Analogie

```
Compiler-Welt          →    noRAG-Welt
─────────────────────────────────────────────
Source Files           →    Dokumente (PDF, Wiki, Slides, ...)
Object Files           →    CKUs (Compiled Knowledge Units)
Linker                 →    Knowledge Structure (verbindet CKUs)
Dependency Graph       →    Weiss welche CKUs voneinander abhaengen
make (incremental)     →    Nur neu-kompilieren was sich geaendert hat
watch mode             →    Quellen ueberwachen, auto-kompilieren
```

### Die 4 Stufen

**1. Watch** — Connectors ueberwachen Dokumentquellen (Dateisystem, Confluence, SharePoint, S3, APIs). Erkennt: neues Dokument, geaendertes Dokument, geloeschtes Dokument.

**2. Compile** — Nur das betroffene Dokument wird (neu-)kompiliert. Das multimodale LLM liest es holistisch und erzeugt/aktualisiert die CKU. Erste Aufnahme = Full Compile. Danach nur Delta.

**3. Link** — Der Linker prueft: Hat sich etwas geaendert, das andere CKUs betrifft? Wenn Dokument A auf Dokument B verweist und B sich aendert, wird A's CKU als "stale" markiert und zur Re-Compilation eingeplant. Dependency Tracking wie bei `make`.

**4. Index** — Die Knowledge Structure (der navigierbare Index ueber alle CKUs) wird aktualisiert. Neue Entitaeten, Beziehungen, Zusammenfassungen fliessen sofort ein.

### Ergebnis

Ein neues Dokument ist innerhalb von Sekunden bis Minuten als kompiliertes Wissen verfuegbar — nicht Stunden wie bei RAG-Reindexierung. Und bei Aenderungen wird nur das Noetige neu kompiliert, nicht alles.

---

## 3. CKU — Compiled Knowledge Unit

Die CKU ist das Herzstueck von noRAG. Sie muss gleichzeitig **maschinenoptimiert** und **menschenlesbar** sein — damit Enterprises das Wissen auditieren koennen.

### Format

Eine CKU ist eine strukturierte YAML-Datei pro Quelldokument:

```yaml
# CKU: onboarding-process-2024.yaml
meta:
  source: "HR/Onboarding-Handbuch-2024.pdf"
  compiled: "2026-03-16T10:30:00Z"
  hash: "a3f8c2..."        # Erkennt Aenderungen am Quelldokument
  type: "pdf/multimodal"
  language: "de"

summaries:
  document: "Beschreibt den 5-stufigen Onboarding-Prozess fuer neue Mitarbeiter..."
  sections:
    - id: "s1"
      title: "Vor dem ersten Tag"
      summary: "IT-Setup, Zugaenge, Buddy-Zuweisung..."

entities:
  - id: "e1"
    name: "Onboarding-Prozess"
    type: "process"
    relations:
      - target: "e2"
        type: "involves"
      - target: "cku:it-security-policy"  # Cross-Dokument!
        type: "references"

facts:
  - id: "f1"
    claim: "Jeder neue Mitarbeiter erhaelt in den ersten 3 Tagen einen Buddy"
    source: { page: 4, section: "s1" }
    confidence: 1.0
    entities: ["e1", "e2"]

visuals:
  - id: "v1"
    type: "flowchart"
    source: { page: 6 }
    description: "5-stufiger Ablauf: Vorbereitung → Erster Tag → Woche 1 → Monat 1 → Abschluss"
    structured_data:
      steps: ["Vorbereitung", "Erster Tag", "Woche 1", "Monat 1", "Abschluss"]
      transitions: [...]
    context: "Illustriert den in Sektion 2 beschriebenen Gesamtprozess"

dependencies:
  - "cku:it-security-policy"    # Fuer den Linker
  - "cku:buddy-program"
```

### Design-Prinzipien

- **Alles in einer Datei** — Fakten, Entitaeten, visuelle Inhalte, Querverweise
- **Strukturiertes Verstaendnis** statt roher Text — mit Provenienz (wo genau im Original steht das?)
- **Filesystem-basiert** — human-readable, git-versionierbar, kein Datenbank-Lock-in
- **Multimodal nativ** — Visuelle Inhalte sind First-Class-Citizens, nicht Anhang
- **Cross-Dokument-Links** — CKUs referenzieren einander fuer den Linker

---

## 4. Query Engine

Die Query Engine ersetzt die Vector Search. Sie beweist, dass noRAG **ohne Embeddings** praeziser und schneller ist.

### Zwei Ebenen

**Ebene 1 — Die Knowledge Map (immer im Speicher)**

Ein leichtgewichtiger, strukturierter Index ueber alle CKUs. Kein Vektorraum — ein navigierbares Verzeichnis:

```yaml
entities:
  "Onboarding-Prozess": ["cku:onboarding-2024", "cku:buddy-program"]
  "IT-Security-Policy": ["cku:it-security", "cku:onboarding-2024"]

topics:
  HR:
    Onboarding: ["cku:onboarding-2024", "cku:buddy-program"]
    Offboarding: ["cku:offboarding-policy"]
  IT:
    Security: ["cku:it-security", "cku:vpn-setup"]

facts_index:
  "Buddy": ["cku:onboarding-2024#f1", "cku:buddy-program#f3"]
```

Simpel. Deterministisch. Microsekunden-Lookup statt Millisekunden-Vektorsuche.

**Ebene 2 — Context Assembly**

```
Frage: "Wie laeuft das Onboarding in den ersten 3 Tagen?"

1. ROUTE   → Entities: "Onboarding" → Topics: "HR/Onboarding"
             → CKUs: [onboarding-2024, buddy-program]

2. NAVIGATE → In den CKUs: relevante Fakten + Sektion-Summaries
             + visuelles Wissen (Flowchart Schritt 1-2)

3. ASSEMBLE → Minimaler, praeziser Kontext:
             3 Fakten, 1 Summary, 1 Prozessbeschreibung
             (~400 Tokens statt ~2000 bei RAG)

4. ANSWER   → Kontext + Frage → beliebiges LLM → Antwort mit Quellenangabe
```

### Vorteile

- **Kein Embedding-Modell** noetig
- **Kein Reranking** noetig
- **Kein "Top-K hoffen"** — exakte Navigation
- **Weniger Tokens** = schneller + guenstiger, weil CKUs bereits verstandenes Wissen enthalten

---

## 5. Architektur & Tech Stack

**Ziel: So einfach wie moeglich starten, so weit wie noetig skalieren.**

### Systemuebersicht

```
┌─────────────────────────────────────────────────┐
│                    noRAG                         │
│                                                  │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐  │
│  │ Connectors│──▶│ Compiler  │──▶│ Knowledge │  │
│  │           │   │  Engine   │   │  Store    │  │
│  │FS/S3/    │   │           │   │           │  │
│  │Confluence/│   │ Multimodal│   │ CKUs      │  │
│  │SharePoint │   │ LLM       │   │ Know. Map │  │
│  └───────────┘   └───────────┘   └───────────┘  │
│                                       │          │
│                                       ▼          │
│                                 ┌───────────┐    │
│                                 │  Query     │    │
│                                 │  Engine    │    │
│                                 │           │    │
│                                 │ REST API  │    │
│                                 │ CLI       │    │
│                                 └───────────┘    │
└─────────────────────────────────────────────────┘
```

### Tech-Entscheidungen

| Komponente | Wahl | Warum |
|---|---|---|
| **Sprache** | Python | AI/ML-Oekosystem, jedes Enterprise hat Python-Devs |
| **CKU-Format** | YAML-Dateien | Human-readable, git-versionierbar, kein DB-Lock-in |
| **Knowledge Map** | SQLite | Zero-Config, performant, ueberall verfuegbar |
| **LLM** | Model-agnostic | Claude, GPT-4, Gemini, oder lokale Modelle (Ollama) |
| **Connectors** | Plugin-System | Erweiterbar, Community kann eigene bauen |
| **API** | FastAPI | Async, schnell, auto-generierte OpenAPI-Docs |
| **Deployment** | Docker oder `pip install` | Ein Befehl, fertig |

### Entwickler-Erfahrung

```bash
pip install norag

# Dokumente kompilieren
norag compile ./documents/

# Einzelnes Dokument nachkompilieren
norag compile ./documents/new-policy.pdf

# Watch-Modus: automatisch neu-kompilieren bei Aenderungen
norag watch ./documents/

# Fragen stellen
norag query "Wie laeuft das Onboarding?"

# API starten
norag serve --port 8080
```

Keine Vector-DB aufsetzen. Kein Embedding-Modell laden. Kein Chunking konfigurieren. **Dokumente rein → Wissen raus.**

---

## 6. Enterprise Features

Was noRAG fuer Unternehmen interessant macht — ohne die Einfachheit zu opfern.

### 1. Provenienz ist eingebaut

Jede Antwort enthaelt exakte Quellenangaben — nicht "irgendwo in Dokument X", sondern `Seite 4, Sektion 2.1, Fakt f1`. Compliance-Teams koennen jede Antwort auditieren. Das ist kein Extra-Feature, sondern eine Konsequenz der CKU-Struktur.

### 2. Data Sovereignty

noRAG laeuft komplett on-premise. Dokumente → lokaler Compiler → lokale CKUs → lokale Query Engine. Kein Byte verlasst das Unternehmen.

Fuer Unternehmen, die auch den LLM-Call lokal halten wollen: noRAG mit Ollama/vLLM = **Zero-External-Dependency**.

### 3. Access Control auf CKU-Ebene

```yaml
meta:
  source: "Vertraulich/Gehaltsbaender-2024.pdf"
  access:
    inherit_from: "source"          # Confluence/SharePoint-Rechte uebernehmen
    roles: ["hr-management"]        # Oder explizit setzen
```

Die Query Engine filtert CKUs **vor** dem Context Assembly. Wer keinen Zugriff hat, fuer den existiert das Wissen nicht in der Antwort.

### 4. Connectors als Plugin-System

```
Mitgeliefert (Core):         Community/Enterprise:
├── filesystem               ├── confluence
├── s3                       ├── sharepoint
├── web/url                  ├── google-drive
└── git-repo                 ├── notion
                             ├── jira
                             └── slack (channel-history)
```

Jeder Connector implementiert ein simples Interface: `watch()`, `fetch()`, `detect_changes()`.

### 5. Audit Log

Jede Query wird geloggt: Wer hat was gefragt, welche CKUs wurden genutzt, welche Fakten flossen in die Antwort. Nicht optional — per Default aktiv.

---

## 7. Open Source Strategie & USP

**Philosophie: Alles was noRAG *ist*, ist offen. Was drauf entsteht, wird zum USP.**

### Was Open Source ist (der komplette Kern)

```
noRAG OSS (MIT oder Apache 2.0)
├── Compiler Engine (vollstaendig)
├── Query Engine (vollstaendig)
├── CKU-Format (offene Spezifikation)
├── Knowledge Map (vollstaendig)
├── CLI (vollstaendig)
├── REST API (vollstaendig)
├── Core-Connectors (FS, S3, Git, Web)
└── Plugin-Interface fuer Community-Connectors
```

Kein "Open Core mit kastriertem Free Tier". Der Kern ist **komplett funktionsfaehig**. Ein Unternehmen kann noRAG installieren und produktiv nutzen, ohne je einen Cent zu zahlen.

### Wo der USP natuerlich entsteht

Sobald Unternehmen noRAG nutzen, kompilieren sie ihr gesamtes Wissen in CKUs. Damit entsteht etwas, das es vorher nicht gab: eine **strukturierte, maschinenlesbare Wissensbasis**. Und genau da wachsen Beduerfnisse, die ueber den Compiler hinausgehen:

| Was organisch entsteht | Warum OSS das nicht loest |
|---|---|
| "Welches Wissen ist veraltet?" | → Braucht Knowledge-Quality-Scoring, Freshness-Analyse |
| "Wo haben wir Wissensluecken?" | → Braucht Gap Detection ueber CKU-Coverage |
| "Wer nutzt welches Wissen?" | → Braucht Analytics-Dashboard, Usage-Tracking |
| "Unsere 50.000 Dokumente kompilieren" | → Braucht optimierte Batch-Compilation, Parallelisierung |
| "Compliance will alles nachvollziehen" | → Braucht Enterprise Audit, Retention Policies |
| "Wir wollen das nicht selbst hosten" | → **noRAG Cloud** |

### Die strategische Idee

Der Compiler ist das Trojanische Pferd. Sobald ein Unternehmen sein Wissen in CKUs hat, ist das die wertvollste strukturierte Datenquelle im Unternehmen. Tools, die auf dieser Datenquelle arbeiten — Analyse, Qualitaetssicherung, Lueckenerkennung — sind der natuerliche naechste Schritt.

**Die CKU-Spezifikation als offener Standard** ist der Schluessel. Wenn CKU das Format wird, in dem Unternehmen Wissen strukturieren — wie Docker das Format wurde, in dem man Software paketiert — dann ist noRAG die Plattform.

---

## 8. MVP-Scope

**Prinzip: Das Minimum, das den Paradigmenwechsel beweist.**

```
MVP = "Ein Ordner Dokumente rein → kompiliertes Wissen → bessere Antworten als RAG"
```

### Drin im MVP

| Komponente | Scope |
|---|---|
| **Compiler** | PDF + Markdown → CKU |
| **CKU-Format** | V1 der Spezifikation — Fakten, Entitaeten, Summaries, Visuals |
| **Knowledge Map** | SQLite-basiert, Entity- und Topic-Lookup |
| **Query Engine** | Navigate → Assemble → Answer mit Quellenangabe |
| **LLM** | Ein Provider (Claude API) + Ollama als lokale Option |
| **CLI** | `compile`, `query` — das wars |

### Bewusst NICHT im MVP

```
✗ Watch-Modus (kommt v0.2)
✗ Connectors ausser Filesystem (kommt v0.2)
✗ REST API / Server-Modus (kommt v0.3)
✗ Access Control (kommt v0.4)
✗ Web UI (kommt viel spaeter, oder Community)
✗ Enterprise Features
```

### Die MVP-Demo

```bash
pip install norag

# 10 PDFs kompilieren (Handbuecher, Policies, Specs)
norag compile ./documents/

# Kompiliert... CKUs erstellt.
# ✓ 10 documents → 10 CKUs (47 entities, 183 facts, 12 visuals)

# Fragen stellen
norag query "Wie laeuft das Onboarding in der ersten Woche?"

# Antwort mit exakten Quellen:
# > In der ersten Woche durchlaeuft der neue Mitarbeiter 3 Phasen...
# > [Quelle: onboarding-2024.pdf, S.4-6, inkl. Flowchart S.6]
```

### Roadmap-Ueberblick

```
v0.1 (MVP)  → compile + query CLI, PDF + Markdown, ein LLM-Provider
v0.2        → watch-Modus, inkrementelle Compilation, weitere Connectors
v0.3        → REST API, Server-Modus, Multi-LLM-Support
v0.4        → Access Control, Audit Log, Enterprise-Grundlagen
v0.5        → norag-bench Benchmark-Kit
v1.0        → Stabile CKU-Spezifikation, Production-Ready
```

---

## 9. Differenzierung

**noRAG spielt nicht im selben Feld — es definiert ein neues.**

### Gegen RAG-Frameworks (LlamaIndex, LangChain, Haystack)

Diese Tools machen RAG einfacher zu bauen. noRAG macht RAG ueberfluessig. Das ist kein besseres Pferd — das ist das Auto.

Sie optimieren Chunking-Strategien, Reranking-Pipelines, Embedding-Modelle. noRAG eliminiert alle drei.

### Gegen Microsoft GraphRAG

| | GraphRAG | noRAG |
|---|---|---|
| Grundlage | RAG + Graph als Ergaenzung | Kein RAG. Komplett anderes Paradigma |
| Embeddings | Ja, immer noch noetig | Nein |
| Vector DB | Ja, immer noch noetig | Nein |
| Chunking | Ja, immer noch noetig | Nein |
| Visuelle Inhalte | Nicht adressiert | First-Class-Citizen |
| Komplexitaet | Hoch (RAG + Graph + Summarization) | Niedrig (Compile + Navigate) |

GraphRAG verbessert RAG. noRAG ersetzt es.

### Gegen grosse Context Windows (Gemini 1M, Claude 200K)

"Alles ins Context Window stopfen" ist die Brute-Force-Loesung. 10.000 Seiten in den Kontext = unbezahlbar. 100 Token kompiliertes Wissen = praeziser UND billiger. Skaliert nicht, keine Struktur, keine Quellenangaben.

### Gegen Fine-Tuning / Knowledge Distillation

| | Fine-Tuning | noRAG |
|---|---|---|
| Update-Speed | Stunden/Tage | Sekunden/Minuten |
| Auditierbar | Nein (in Weights vergraben) | Ja (CKU ist lesbar) |
| Model-agnostisch | Nein (an ein Modell gebunden) | Ja (jedes LLM) |
| Kosten | Hoch (GPU-Training) | Niedrig (ein LLM-Call pro Dokument) |

### noRAGs einzigartige Position

```
1. Eliminiert die RAG-Pipeline    (statt sie zu optimieren)
2. Multimodal nativ               (statt Text-only)
3. Auditierbares Wissen           (statt Black-Box)
4. Compile-Time statt Runtime     (statt bei jeder Query zu suchen)
5. Model-agnostisch               (statt LLM-Lock-in)
6. Offene CKU-Spezifikation       (statt proprietaeres Format)
```

---

## 10. Validierung & Benchmarks

**Behauptungen ohne Beweis sind Marketing. noRAG muss messbar besser sein.**

### Benchmark-Ansatz: `norag-bench`

Ein offenes Benchmark-Kit, das jeder selbst ausfuehren kann. noRAG vs. RAG, gleiche Dokumente, gleiche Fragen, gleiche LLMs.

```bash
norag bench --compare-with rag --dataset enterprise-docs-50
```

### 6 Dimensionen

**1. Answer Quality**

```
Testset: 200 Fragen ueber 50 Enterprise-Dokumente
Metrik:  Korrektheit, Vollstaendigkeit, Halluzinationsrate
Ziel:    noRAG ≥ 90% korrekt, RAG-Baseline typisch 60-75%
```

**2. Visual Knowledge (Killerfeature)**

```
Testset: 50 Fragen, die NUR mit visuellem Inhalt beantwortbar sind
Metrik:  Korrektheit
Ziel:    noRAG ≥ 85%, RAG ~0%
```

**3. Token-Effizienz**

```
Metrik:  Tokens im Prompt pro Query
Ziel:    noRAG ≤ 500 Tokens vs RAG ~2000-4000 Tokens
         → 4-8x weniger Tokens = 4-8x guenstiger pro Query
```

**4. Latenz (Query-Time)**

```
Metrik:  Zeit von Frage bis Antwort (ohne LLM-Latenz)
Ziel:    noRAG < 50ms vs RAG 200-500ms
```

**5. Cross-Document Reasoning**

```
Testset: 50 Fragen, die Wissen aus 2-3 Dokumenten kombinieren
Ziel:    noRAG ≥ 80% vs RAG ~30-40%
```

**6. Time-to-Value**

```
Metrik:  Zeit von "ich habe Dokumente" bis "erste korrekte Antwort"
Ziel:    noRAG < 5 Minuten vs RAG 30-60 Minuten
```

### Benchmark-Strategie fuer Adoption

```
Phase 1 (MVP):       Eigene Benchmarks, publiziert im Repo
Phase 2 (Community): norag-bench als offenes Benchmark-Kit
Phase 3 (Credibility): Vergleich auf etablierten Benchmarks (MTEB, BEIR)
```

---

## Zusammenfassung

noRAG ist ein Knowledge Compiler, der das RAG-Paradigma durch einen fundamental anderen Ansatz ersetzt: **Compile, don't search.** Dokumente werden bei der Aufnahme holistisch verstanden — inklusive visueller Inhalte — und in strukturierte, maschinenoptimierte Compiled Knowledge Units (CKUs) uebersetzt. Bei Fragen wird die Wissensstruktur navigiert statt durchsucht, was praezisere Antworten mit weniger Tokens liefert.

Der Open-Source-Kern ist komplett funktionsfaehig. Der natuerliche USP entsteht aus der strukturierten Wissensbasis, die Unternehmen durch die Nutzung aufbauen — und den Tools, die auf dieser Basis arbeiten.

**Der One-Liner:**

> *noRAG compiles documents into machine-optimized knowledge. No vectors. No chunks. No embeddings. Just understanding.*
