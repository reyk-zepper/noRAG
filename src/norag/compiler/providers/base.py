"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod

from norag.compiler.parsers.base import ParsedDocument


class LLMProvider(ABC):
    """Abstract LLM provider for knowledge compilation and query answering."""

    @abstractmethod
    def compile_document(self, document: ParsedDocument) -> dict:
        """
        Send parsed document to LLM and get structured CKU data back.

        Builds a prompt from all pages (markdown text + visual element
        descriptions) and instructs the LLM to return a JSON object that
        matches the CKU schema (minus the `meta` section, which is filled in
        by the compiler).

        Returns a dict with keys:
            summaries, entities, facts, visuals, dependencies
        Will be validated by CKU's Pydantic model downstream.
        """
        ...

    @abstractmethod
    def answer_query(self, question: str, context: str) -> str:
        """
        Given a question and assembled context from CKUs, generate an answer.

        Args:
            question: The user's natural-language question.
            context:  Pre-assembled context string built from relevant CKU
                      sections (summaries, facts, entities, visuals).

        Returns the answer text, including source citations where possible.
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return a human-readable provider identifier (e.g. 'claude', 'ollama')."""
        ...
