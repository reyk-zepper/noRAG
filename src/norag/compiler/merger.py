"""CKU Merger — combines multiple section-level CKU dicts into one document CKU.

After splitting a large document and compiling each section independently,
the merger reassembles the results into a single coherent CKU dict.
"""

from __future__ import annotations

from typing import Any


def merge_cku_dicts(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge a list of partial CKU dicts into one unified CKU dict.

    Args:
        chunks: List of raw CKU dicts as returned by ``LLMProvider.compile_document``.

    Returns:
        A single merged CKU dict with deduplicated entities and combined
        summaries, facts, visuals, and dependencies.
    """
    if not chunks:
        return _empty_cku()

    if len(chunks) == 1:
        return chunks[0]

    merged: dict[str, Any] = {
        "summaries": _merge_summaries(chunks),
        "entities": _merge_entities(chunks),
        "facts": _merge_facts(chunks),
        "visuals": _merge_visuals(chunks),
        "dependencies": _merge_dependencies(chunks),
        "language": _pick_language(chunks),
    }
    return merged


def _empty_cku() -> dict[str, Any]:
    return {
        "summaries": {"document": "", "sections": []},
        "entities": [],
        "facts": [],
        "visuals": [],
        "dependencies": [],
        "language": "en",
    }


# ------------------------------------------------------------------
# Summaries
# ------------------------------------------------------------------


def _merge_summaries(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine section summaries; build a document summary from parts."""
    all_sections: list[dict] = []
    doc_parts: list[str] = []

    for chunk in chunks:
        raw = chunk.get("summaries", {})
        if not isinstance(raw, dict):
            continue
        doc_text = raw.get("document", "")
        if doc_text:
            doc_parts.append(str(doc_text))
        sections = raw.get("sections", [])
        if isinstance(sections, list):
            all_sections.extend(s for s in sections if isinstance(s, dict))

    # Deduplicate sections by id
    seen_ids: set[str] = set()
    unique_sections: list[dict] = []
    for sec in all_sections:
        sid = sec.get("id", "")
        if sid and sid in seen_ids:
            continue
        if sid:
            seen_ids.add(sid)
        unique_sections.append(sec)

    return {
        "document": " ".join(doc_parts),
        "sections": unique_sections,
    }


# ------------------------------------------------------------------
# Entities
# ------------------------------------------------------------------


def _merge_entities(chunks: list[dict[str, Any]]) -> list[dict]:
    """Merge entities from all chunks, deduplicating by id."""
    seen: dict[str, dict] = {}
    for chunk in chunks:
        entities = chunk.get("entities", [])
        if not isinstance(entities, list):
            continue
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            eid = entity.get("id", "")
            if not eid:
                continue
            if eid in seen:
                # Merge relations from duplicate
                existing_relations = seen[eid].get("relations", [])
                new_relations = entity.get("relations", [])
                if isinstance(new_relations, list):
                    existing_targets = {
                        (r.get("target"), r.get("type"))
                        for r in existing_relations
                        if isinstance(r, dict)
                    }
                    for r in new_relations:
                        if isinstance(r, dict):
                            key = (r.get("target"), r.get("type"))
                            if key not in existing_targets:
                                existing_relations.append(r)
                                existing_targets.add(key)
                    seen[eid]["relations"] = existing_relations
            else:
                seen[eid] = entity
    return list(seen.values())


# ------------------------------------------------------------------
# Facts
# ------------------------------------------------------------------


def _merge_facts(chunks: list[dict[str, Any]]) -> list[dict]:
    """Concatenate facts from all chunks, deduplicating by id."""
    seen: dict[str, dict] = {}
    for chunk in chunks:
        facts = chunk.get("facts", [])
        if not isinstance(facts, list):
            continue
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            fid = fact.get("id", "")
            if fid and fid in seen:
                continue
            if fid:
                seen[fid] = fact
            else:
                seen[f"_anon_{id(fact)}"] = fact
    return list(seen.values())


# ------------------------------------------------------------------
# Visuals
# ------------------------------------------------------------------


def _merge_visuals(chunks: list[dict[str, Any]]) -> list[dict]:
    """Concatenate visuals from all chunks, deduplicating by id."""
    seen: dict[str, dict] = {}
    for chunk in chunks:
        visuals = chunk.get("visuals", [])
        if not isinstance(visuals, list):
            continue
        for vis in visuals:
            if not isinstance(vis, dict):
                continue
            vid = vis.get("id", "")
            if vid and vid in seen:
                continue
            if vid:
                seen[vid] = vis
            else:
                seen[f"_anon_{id(vis)}"] = vis
    return list(seen.values())


# ------------------------------------------------------------------
# Dependencies & Language
# ------------------------------------------------------------------


def _merge_dependencies(chunks: list[dict[str, Any]]) -> list[str]:
    """Collect unique dependencies from all chunks."""
    deps: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        raw = chunk.get("dependencies", [])
        if not isinstance(raw, list):
            continue
        for dep in raw:
            s = str(dep)
            if s not in seen:
                deps.append(s)
                seen.add(s)
    return deps


def _pick_language(chunks: list[dict[str, Any]]) -> str:
    """Pick the most common language across chunks."""
    counts: dict[str, int] = {}
    for chunk in chunks:
        lang = chunk.get("language", "en")
        if isinstance(lang, str):
            counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return "en"
    return max(counts, key=counts.get)  # type: ignore[arg-type]
