"""Query Engine — orchestrates Route → Assemble → Answer."""

from pathlib import Path
from dataclasses import dataclass

from norag.config import Config
from norag.store import CKUStore, KnowledgeMap
from norag.query.router import Router
from norag.query.assembler import Assembler, AssembledContext
from norag.compiler.providers import get_provider


@dataclass
class QueryResult:
    answer: str
    context: AssembledContext
    routed_ckus: list[str]


class QueryEngine:
    """Orchestrates the noRAG query pipeline: Route → Assemble → Answer."""

    def __init__(self, config: Config):
        self.config = config
        self.store = CKUStore(config.ckus_dir)
        self.knowledge_map = KnowledgeMap(config.db_path)
        self.router = Router(self.knowledge_map)
        self.assembler = Assembler(self.store)
        provider_kwargs: dict = {"api_key": config.api_key, "model": config.model}
        if config.provider == "ollama":
            provider_kwargs["host"] = config.ollama_host
        self.provider = get_provider(config.provider, **provider_kwargs)

    def query(self, question: str, top_k: int = 5, user_role: str = "") -> QueryResult:
        """
        Answer a question using compiled knowledge.

        Pipeline:
        1. ROUTE    — Find relevant CKUs via knowledge map
        2. FILTER   — Remove CKUs the user has no access to
        3. ASSEMBLE — Extract minimal context from CKUs
        4. ANSWER   — Send context + question to LLM

        Args:
            question:  Natural-language question.
            top_k:     Maximum number of CKUs to consider.
            user_role: Role of the querying user (empty = anonymous).
                       CKUs with no roles are public.  CKUs with roles
                       are only visible if *user_role* matches.
        """
        # 1. Route
        cku_ids = self.router.route(question, top_k=top_k)

        # 2. Filter by access control
        if user_role or True:  # always filter — public CKUs pass through
            cku_ids = self._filter_by_access(cku_ids, user_role)

        if not cku_ids:
            return QueryResult(
                answer="No relevant knowledge found. Have you compiled documents?",
                context=AssembledContext(),
                routed_ckus=[],
            )

        # 3. Assemble
        context = self.assembler.assemble(cku_ids, question)

        # 4. Answer
        prompt_context = context.to_prompt_context()
        answer = self.provider.answer_query(question, prompt_context)

        return QueryResult(
            answer=answer,
            context=context,
            routed_ckus=cku_ids,
        )

    def _filter_by_access(self, cku_ids: list[str], user_role: str) -> list[str]:
        """Filter CKU IDs by access control.

        - CKUs with empty roles list are public (always visible).
        - CKUs with roles are only visible if *user_role* is in the list.
        """
        filtered: list[str] = []
        for cku_id in cku_ids:
            try:
                cku = self.store.load(cku_id)
            except FileNotFoundError:
                continue
            roles = cku.meta.access.roles
            if not roles or user_role in roles:
                filtered.append(cku_id)
        return filtered
