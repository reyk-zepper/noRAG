"""LLM provider adapters — Claude, Ollama, and other backends."""

from norag.compiler.providers.base import LLMProvider


def get_provider(name: str, **kwargs) -> LLMProvider:
    """
    Factory to instantiate an LLM provider by name.

    Args:
        name:    Provider identifier — 'claude' or 'ollama'.
        **kwargs: Forwarded verbatim to the provider constructor.

    Claude kwargs:
        api_key (str | None): Anthropic API key; falls back to ANTHROPIC_API_KEY env var.
        model   (str):        Model ID, default 'claude-sonnet-4-20250514'.

    Ollama kwargs:
        host  (str): Ollama base URL, default 'http://localhost:11434'.
        model (str): Model name, default 'llama3.1'.

    Raises:
        ValueError: If the provider name is not recognised.
    """
    if name == "claude":
        from norag.compiler.providers.claude import ClaudeProvider
        claude_kwargs = {k: v for k, v in kwargs.items() if k in ("api_key", "model")}
        return ClaudeProvider(**claude_kwargs)
    elif name == "ollama":
        from norag.compiler.providers.ollama import OllamaProvider
        ollama_kwargs = {k: v for k, v in kwargs.items() if k in ("host", "model")}
        return OllamaProvider(**ollama_kwargs)
    else:
        raise ValueError(
            f"Unknown provider: {name!r}. Available providers: claude, ollama"
        )


__all__ = ["LLMProvider", "get_provider"]
