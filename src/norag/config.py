"""noRAG configuration — loaded from env vars (NORAG_ prefix) and .norag/config.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Config:
    store_dir: Path = field(default_factory=lambda: Path.cwd() / ".norag")
    provider: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    ollama_host: str = "http://localhost:11434"
    max_section_lines: int = 200

    # Derived paths — computed after __post_init__
    ckus_dir: Path = field(init=False)
    db_path: Path = field(init=False)
    audit_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.store_dir = Path(self.store_dir)
        self.ckus_dir = self.store_dir / "ckus"
        self.db_path = self.store_dir / "knowledge.db"
        self.audit_path = self.store_dir / "audit.db"


def load_config(store_dir: Optional[Path] = None) -> Config:
    """Load config from .norag/config.yaml and environment variables.

    Priority (highest wins):
      1. Environment variables (NORAG_ prefix)
      2. .norag/config.yaml
      3. Built-in defaults
    """
    # Start with defaults
    cfg: dict = {}

    # Resolve store_dir early so we can find the config file
    env_store = os.environ.get("NORAG_STORE_DIR")
    resolved_store = Path(store_dir or env_store or Path.cwd() / ".norag")

    # Load from config file if present
    config_file = resolved_store / "config.yaml"
    if config_file.exists():
        with config_file.open() as fh:
            file_cfg = yaml.safe_load(fh) or {}
        cfg.update(file_cfg)

    # Override with environment variables
    env_map = {
        "NORAG_STORE_DIR": "store_dir",
        "NORAG_PROVIDER": "provider",
        "NORAG_MODEL": "model",
        "NORAG_API_KEY": "api_key",
        "NORAG_OLLAMA_HOST": "ollama_host",
        "NORAG_MAX_SECTION_LINES": "max_section_lines",
        # Convenience aliases
        "ANTHROPIC_API_KEY": "api_key",
        "OLLAMA_HOST": "ollama_host",
    }
    for env_key, cfg_key in env_map.items():
        value = os.environ.get(env_key)
        if value is not None:
            # Alias keys only set their target if not already set by a NORAG_ key
            if env_key == "ANTHROPIC_API_KEY" and "api_key" in cfg:
                continue
            if env_key == "OLLAMA_HOST" and "ollama_host" in cfg:
                continue
            cfg[cfg_key] = value

    # Explicit store_dir argument always wins
    if store_dir is not None:
        cfg["store_dir"] = store_dir

    # Cast numeric fields from string env vars
    if "max_section_lines" in cfg:
        try:
            cfg["max_section_lines"] = int(cfg["max_section_lines"])
        except (TypeError, ValueError):
            cfg.pop("max_section_lines")

    # Build dataclass — only pass known init fields
    init_fields = {"store_dir", "provider", "model", "api_key", "ollama_host", "max_section_lines"}
    filtered = {k: v for k, v in cfg.items() if k in init_fields}

    return Config(**filtered)
