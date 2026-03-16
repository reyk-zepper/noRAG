"""Claude provider — uses the Anthropic SDK to compile documents and answer queries."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from norag.compiler.parsers.base import ParsedDocument
from norag.compiler.providers.base import LLMProvider

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_COMPILE_SYSTEM_PROMPT = """\
You are a Knowledge Compiler. Your task is to analyze a document holistically — \
text, structure, and visuals — and extract all relevant knowledge into a strictly \
typed JSON structure.

The JSON object you return MUST have exactly these top-level keys:

{
  "summaries": {
    "document": "<one-paragraph holistic summary of the entire document>",
    "sections": [
      {
        "id": "<short slug, e.g. 'intro' or 'section-1'>",
        "title": "<section heading>",
        "summary": "<concise summary of this section>"
      }
    ]
  },
  "entities": [
    {
      "id": "<unique slug, e.g. 'entity-1'>",
      "name": "<canonical name>",
      "type": "<one of: person | organization | system | process | concept | product | location | event | other>",
      "relations": [
        {
          "target": "<id of another entity>",
          "type": "<relation label, e.g. 'uses', 'belongs_to', 'depends_on'>"
        }
      ]
    }
  ],
  "facts": [
    {
      "id": "<unique slug, e.g. 'fact-1'>",
      "claim": "<a single, self-contained factual statement>",
      "source": {
        "page": <1-based page number or null>,
        "section": "<section id or null>"
      },
      "confidence": <float between 0.0 and 1.0>,
      "entities": ["<entity id>", ...]
    }
  ],
  "visuals": [
    {
      "id": "<unique slug, e.g. 'visual-1'>",
      "type": "<one of: flowchart | table | diagram | chart | image | screenshot | other>",
      "source": {
        "page": <1-based page number or null>,
        "section": "<section id or null>"
      },
      "description": "<detailed description of what the visual shows>",
      "structured_data": <JSON object with extracted data when applicable, or null>,
      "context": "<surrounding textual context that explains the visual, or null>"
    }
  ],
  "dependencies": ["<referenced document id or filename>", ...]
}

Rules:
- EVERY list may be empty ([]) but must be present.
- "dependencies" lists documents explicitly referenced or imported by this document.
- "entities" relations must only reference entity IDs defined within the same list.
- "facts.entities" must only reference entity IDs defined in the entities list.
- Confidence 1.0 = explicitly stated; 0.7–0.9 = strongly implied; <0.7 = inferred.
- Do NOT include the "meta" section — that is filled in by the compiler.
- Respond ONLY with the raw JSON object. No markdown fences, no prose, no commentary.\
"""

_COMPILE_USER_TEMPLATE = """\
Analyze the following document and return the structured JSON knowledge object.

Document: {source_path}
Total pages: {page_count}
Type: {doc_type}

=== DOCUMENT CONTENT ===

{content}

=== END OF DOCUMENT ===

Respond ONLY with valid JSON matching the schema described in the system prompt.\
"""

_QUERY_SYSTEM_PROMPT = """\
You are a precise knowledge assistant. You answer questions strictly based on the \
provided context, which was compiled from structured knowledge units (CKUs).

Rules:
- Base your answer entirely on the provided context.
- If the context does not contain enough information, say so explicitly.
- Always cite your sources using the format [page X] or [section: name] when available.
- Be concise but complete.\
"""

_QUERY_USER_TEMPLATE = """\
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
    """
    Strip markdown code fences if present and return the bare JSON string.
    Claude occasionally wraps output in ```json ... ``` despite instructions.
    """
    # Remove ```json ... ``` or ``` ... ``` wrappers
    fenced = re.match(r"^\s*```(?:json)?\s*([\s\S]*?)```\s*$", text.strip())
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class ClaudeProvider(LLMProvider):
    """LLM provider backed by Anthropic's Claude models."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        try:
            import anthropic  # noqa: F401 — verify import before storing
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for ClaudeProvider. "
                "Install it with:  pip install anthropic"
            ) from exc

        import anthropic as _anthropic  # type: ignore[import]

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "No Anthropic API key provided. Pass api_key= or set the "
                "ANTHROPIC_API_KEY environment variable."
            )

        self._client = _anthropic.Anthropic(api_key=resolved_key)
        self._model = model

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    def compile_document(self, document: ParsedDocument) -> dict:
        """Compile a ParsedDocument into a raw CKU dict via Claude."""
        content = _build_document_content(document)
        user_message = _COMPILE_USER_TEMPLATE.format(
            source_path=document.source_path,
            page_count=document.page_count,
            doc_type=document.doc_type,
            content=content,
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=8192,
            system=_COMPILE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text
        return self._parse_json_response(raw_text, context="compile_document")

    def answer_query(self, question: str, context: str) -> str:
        """Answer a question using the provided CKU context."""
        user_message = _QUERY_USER_TEMPLATE.format(
            context=context,
            question=question,
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_QUERY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text.strip()

    def get_name(self) -> str:
        return "claude"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_json_response(self, raw: str, context: str) -> dict[str, Any]:
        cleaned = _extract_json(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"ClaudeProvider.{context}: LLM returned invalid JSON.\n"
                f"Parse error: {exc}\n"
                f"Raw response (first 500 chars):\n{raw[:500]}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"ClaudeProvider.{context}: Expected a JSON object, got {type(data).__name__}."
            )
        return data
