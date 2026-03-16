"""Ollama provider — uses httpx to talk to a local Ollama instance."""

from __future__ import annotations

import json
import re
from typing import Any

from norag.compiler.parsers.base import ParsedDocument
from norag.compiler.providers.base import LLMProvider

# ---------------------------------------------------------------------------
# Prompts  (same structure as Claude provider, adapted for single-turn chat)
# ---------------------------------------------------------------------------

_COMPILE_PROMPT_TEMPLATE = """\
You are a Knowledge Compiler. Analyze the following document holistically — \
text, structure, and visuals — and extract all relevant knowledge into a \
strictly typed JSON structure.

The JSON object you return MUST have exactly these top-level keys:

{{
  "summaries": {{
    "document": "<one-paragraph holistic summary>",
    "sections": [
      {{
        "id": "<short slug>",
        "title": "<section heading>",
        "summary": "<concise section summary>"
      }}
    ]
  }},
  "entities": [
    {{
      "id": "<unique slug, e.g. 'entity-1'>",
      "name": "<canonical name>",
      "type": "<person|organization|system|process|concept|product|location|event|other>",
      "relations": [
        {{
          "target": "<entity id>",
          "type": "<relation label>"
        }}
      ]
    }}
  ],
  "facts": [
    {{
      "id": "<unique slug, e.g. 'fact-1'>",
      "claim": "<single self-contained factual statement>",
      "source": {{
        "page": <1-based page number or null>,
        "section": "<section id or null>"
      }},
      "confidence": <float 0.0–1.0>,
      "entities": ["<entity id>", ...]
    }}
  ],
  "visuals": [
    {{
      "id": "<unique slug>",
      "type": "<flowchart|table|diagram|chart|image|screenshot|other>",
      "source": {{
        "page": <1-based page number or null>,
        "section": "<section id or null>"
      }},
      "description": "<detailed description>",
      "structured_data": <JSON object or null>,
      "context": "<surrounding context or null>"
    }}
  ],
  "dependencies": ["<referenced document id or filename>", ...]
}}

Rules:
- Every list may be empty but must be present.
- "entities" relations reference only IDs from the entities list.
- "facts.entities" reference only IDs from the entities list.
- Confidence: 1.0=explicit, 0.7-0.9=strongly implied, <0.7=inferred.
- Do NOT include a "meta" section.
- Respond ONLY with the raw JSON object. No markdown fences, no prose.

=== DOCUMENT: {source_path} (type: {doc_type}, {page_count} pages) ===

{content}

=== END OF DOCUMENT ===

Respond ONLY with valid JSON:\
"""

_QUERY_PROMPT_TEMPLATE = """\
You are a precise knowledge assistant. Answer the question strictly based on \
the provided context. Cite sources using [page X] or [section: name] format. \
If the context lacks enough information, say so explicitly.

Context (compiled knowledge):
---
{context}
---

Question: {question}

Answer:\
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_document_content(document: ParsedDocument) -> str:
    """Render all pages as a single annotated markdown string."""
    parts: list[str] = []
    for page in document.pages:
        parts.append(f"## Page {page.number}\n")
        parts.append(page.text_markdown.strip())

        if page.visuals:
            parts.append("\n### Visual Elements on this page\n")
            for i, v in enumerate(page.visuals, start=1):
                desc_parts = [f"- **Visual {i}** (type: {v.type})"]
                if v.data:
                    desc_parts.append(f"  Data/Content:\n{v.data}")
                parts.append("\n".join(desc_parts))

        parts.append("")  # blank line between pages

    return "\n".join(parts)


def _extract_json(text: str) -> str:
    """Strip markdown code fences if present."""
    fenced = re.match(r"^\s*```(?:json)?\s*([\s\S]*?)```\s*$", text.strip())
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama instance (no SDK — pure HTTP)."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.1",
        api_key: str | None = None,  # accepted but ignored (Ollama is local/keyless)
        **kwargs,  # absorb any other unexpected kwargs gracefully
    ) -> None:
        try:
            import httpx  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "The 'httpx' package is required for OllamaProvider. "
                "Install it with:  pip install httpx"
            ) from exc

        self._host = host.rstrip("/")
        self._model = model

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    def compile_document(self, document: ParsedDocument) -> dict:
        """Compile a ParsedDocument into a raw CKU dict via Ollama."""
        content = _build_document_content(document)
        prompt = _COMPILE_PROMPT_TEMPLATE.format(
            source_path=document.source_path,
            page_count=document.page_count,
            doc_type=document.doc_type,
            content=content,
        )
        raw = self._generate(prompt)
        return self._parse_json_response(raw, context="compile_document")

    def answer_query(self, question: str, context: str) -> str:
        """Answer a question using the provided CKU context."""
        prompt = _QUERY_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )
        return self._generate(prompt).strip()

    def get_name(self) -> str:
        return "ollama"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate(self, prompt: str) -> str:
        """
        POST to /api/generate with stream=False.
        Falls back to /api/chat if the generate endpoint is unavailable.
        Raises ConnectionError on network problems.
        """
        import httpx  # type: ignore[import]

        url = f"{self._host}/api/generate"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # low temperature for structured extraction
                "num_predict": 8192,
            },
        }

        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(url, json=payload)

            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"OllamaProvider: Cannot connect to Ollama at {self._host}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"OllamaProvider: HTTP {exc.response.status_code} from Ollama. "
                f"Response: {exc.response.text[:200]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"OllamaProvider: Request to Ollama timed out after 300 s. "
                "Consider using a smaller model or increasing the timeout."
            ) from exc

    def _parse_json_response(self, raw: str, context: str) -> dict[str, Any]:
        cleaned = _extract_json(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"OllamaProvider.{context}: LLM returned invalid JSON.\n"
                f"Parse error: {exc}\n"
                f"Raw response (first 500 chars):\n{raw[:500]}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"OllamaProvider.{context}: Expected a JSON object, got {type(data).__name__}."
            )
        return data
