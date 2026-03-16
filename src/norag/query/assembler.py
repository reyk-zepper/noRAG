"""Query Assembler — extracts minimal, precise context from CKUs for answering a question."""

from norag.store import CKUStore
from norag.models.cku import CKU


class AssembledContext:
    """Context assembled from CKUs for answering a query."""

    def __init__(self):
        self.facts: list[dict] = []       # {claim, source, cku_source}
        self.summaries: list[dict] = []   # {summary, cku_source}
        self.visuals: list[dict] = []     # {description, type, cku_source}
        self.sources: list[str] = []      # unique source documents

    def to_prompt_context(self) -> str:
        """Format assembled knowledge as a prompt context string."""
        parts = []

        if self.summaries:
            parts.append("## Relevant Summaries")
            for s in self.summaries:
                parts.append(f"- {s['summary']} [Source: {s['cku_source']}]")

        if self.facts:
            parts.append("\n## Relevant Facts")
            for f in self.facts:
                source_info = ""
                if f.get("source"):
                    source_info = f" (p.{f['source'].get('page', '?')})"
                parts.append(f"- {f['claim']}{source_info} [Source: {f['cku_source']}]")

        if self.visuals:
            parts.append("\n## Visual Knowledge")
            for v in self.visuals:
                parts.append(f"- [{v['type']}] {v['description']} [Source: {v['cku_source']}]")

        return "\n".join(parts)

    @property
    def token_estimate(self) -> int:
        """Rough token estimate (words / 0.75)."""
        text = self.to_prompt_context()
        return int(len(text.split()) / 0.75)


class Assembler:
    """Assembles minimal, precise context from CKUs."""

    def __init__(self, store: CKUStore):
        self.store = store

    def assemble(self, cku_ids: list[str], question: str) -> AssembledContext:
        """
        Load CKUs and extract the most relevant knowledge for the question.

        For each CKU:
        1. Include the document summary
        2. Include all facts (already compiled/distilled)
        3. Include visual descriptions
        4. Track sources for citation
        """
        ctx = AssembledContext()

        for cku_id in cku_ids:
            try:
                cku = self.store.load(cku_id)
            except FileNotFoundError:
                continue

            source = cku.meta.source
            if source not in ctx.sources:
                ctx.sources.append(source)

            # Document summary
            ctx.summaries.append({
                "summary": cku.summaries.document,
                "cku_source": source,
            })

            # All facts
            for fact in cku.facts:
                ctx.facts.append({
                    "claim": fact.claim,
                    "source": fact.source.model_dump() if fact.source else None,
                    "cku_source": source,
                })

            # Visual descriptions
            for visual in cku.visuals:
                ctx.visuals.append({
                    "description": visual.description,
                    "type": visual.type,
                    "cku_source": source,
                })

        return ctx
