"""Benchmark dataset — loads and validates benchmark data.

Dataset directory structure:
    dataset/
    ├── docs/          # documents to compile (.md, .pdf)
    │   ├── doc1.md
    │   └── doc2.pdf
    └── questions.json  # questions with expected answers

questions.json schema:
    [
        {
            "id": "q1",
            "question": "What is X?",
            "expected_keywords": ["keyword1", "keyword2"],
            "category": "answer_quality|visual|cross_document",
            "difficulty": "easy|medium|hard"
        }
    ]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BenchQuestion(BaseModel):
    """A single benchmark question."""

    id: str
    question: str
    expected_keywords: list[str] = Field(default_factory=list)
    category: str = "answer_quality"
    difficulty: str = "medium"


class BenchDataset(BaseModel):
    """A loaded benchmark dataset."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    docs_dir: Path
    questions: list[BenchQuestion]
    doc_files: list[Path]


def load_dataset(dataset_path: Path) -> BenchDataset:
    """Load a benchmark dataset from a directory.

    Args:
        dataset_path: Path to the dataset directory.

    Returns:
        A validated BenchDataset.

    Raises:
        FileNotFoundError: If the dataset or required files are missing.
        ValueError: If questions.json is malformed.
    """
    dataset_path = dataset_path.resolve()

    if not dataset_path.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_path}")

    docs_dir = dataset_path / "docs"
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"docs/ subdirectory not found in {dataset_path}")

    questions_file = dataset_path / "questions.json"
    if not questions_file.exists():
        raise FileNotFoundError(f"questions.json not found in {dataset_path}")

    # Load questions
    raw = json.loads(questions_file.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("questions.json must contain a JSON array")

    questions = [BenchQuestion.model_validate(q) for q in raw]

    if not questions:
        raise ValueError("questions.json must contain at least one question")

    # Collect document files
    supported = {".md", ".markdown", ".pdf"}
    doc_files = sorted(
        p for p in docs_dir.iterdir()
        if p.is_file() and p.suffix.lower() in supported
    )

    if not doc_files:
        raise FileNotFoundError(f"No supported documents found in {docs_dir}")

    return BenchDataset(
        name=dataset_path.name,
        docs_dir=docs_dir,
        questions=questions,
        doc_files=doc_files,
    )
