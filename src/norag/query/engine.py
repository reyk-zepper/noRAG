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

    def query(self, question: str, top_k: int = 5) -> QueryResult:
        """
        Answer a question using compiled knowledge.

        Pipeline:
        1. ROUTE    — Find relevant CKUs via knowledge map
        2. ASSEMBLE — Extract minimal context from CKUs
        3. ANSWER   — Send context + question to LLM
        """
        # 1. Route
        cku_ids = self.router.route(question, top_k=top_k)

        if not cku_ids:
            return QueryResult(
                answer="No relevant knowledge found. Have you compiled documents?",
                context=AssembledContext(),
                routed_ckus=[],
            )

        # 2. Assemble
        context = self.assembler.assemble(cku_ids, question)

        # 3. Answer
        prompt_context = context.to_prompt_context()
        answer = self.provider.answer_query(question, prompt_context)

        return QueryResult(
            answer=answer,
            context=context,
            routed_ckus=cku_ids,
        )
