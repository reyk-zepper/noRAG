"""Query Router — maps a natural language question to relevant CKU IDs."""

from norag.store import KnowledgeMap
import re


class Router:
    """Routes a question to relevant CKUs by navigating the knowledge map."""

    def __init__(self, knowledge_map: KnowledgeMap):
        self.km = knowledge_map

    def route(self, question: str, top_k: int = 5) -> list[str]:
        """
        Find the most relevant CKU IDs for a question.

        Strategy (multi-signal):
        1. Extract keywords from the question (split, remove stopwords)
        2. Search entities by keywords                 (weight 3)
        3. Search topics by keywords                   (weight 2)
        4. Full-text search on facts / keywords        (weight 1)
        5. Merge results, deduplicate, rank by score
        6. Return top_k CKU IDs
        """
        keywords = self._extract_keywords(question)

        cku_scores: dict[str, float] = {}

        # Signal 1: Entity matches (weight 3)
        for kw in keywords:
            for cku_id in self.km.find_by_entity(kw):
                cku_scores[cku_id] = cku_scores.get(cku_id, 0) + 3.0

        # Signal 2: Topic matches (weight 2)
        for kw in keywords:
            for cku_id in self.km.find_by_topic(kw):
                cku_scores[cku_id] = cku_scores.get(cku_id, 0) + 2.0

        # Signal 3: Fact keyword search (weight 1)
        if keywords:
            for cku_id in self.km.find_by_keywords(keywords):
                cku_scores[cku_id] = cku_scores.get(cku_id, 0) + 1.0

        # Rank by score descending, return top_k IDs
        ranked = sorted(cku_scores.items(), key=lambda x: x[1], reverse=True)
        return [cku_id for cku_id, _ in ranked[:top_k]]

    def _extract_keywords(self, question: str) -> list[str]:
        """Extract meaningful keywords from a question."""
        stopwords = {
            # English
            "what", "how", "when", "where", "who", "which", "why", "is", "are",
            "was", "were", "do", "does", "did", "the", "a", "an", "in", "on",
            "at", "to", "for", "of", "with", "by", "from", "and", "or", "but",
            "not", "this", "that", "it", "its", "can", "could", "would", "should",
            "has", "have", "had", "be", "been", "being", "will", "shall",
            # German
            "wie", "was", "wer", "wo", "wann", "warum", "ist", "sind", "der",
            "die", "das", "ein", "eine", "in", "auf", "an", "zu", "fuer", "von",
            "mit", "und", "oder", "aber", "nicht", "den", "dem", "des", "im",
            "am", "es", "er", "sie", "wird", "werden", "hat", "haben", "kann",
        }

        words = re.findall(r'\b\w+\b', question.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords
