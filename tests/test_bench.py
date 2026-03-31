"""Unit tests for noRAG benchmark kit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from norag.bench.dataset import BenchDataset, BenchQuestion, load_dataset
from norag.bench.metrics import BenchResults, QuestionResult, compute_keyword_score


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_dataset(tmp_path: Path) -> Path:
    """Create a minimal valid dataset directory."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "test.md").write_text("# Test\nSome content about Python and testing.")

    questions = [
        {
            "id": "q1",
            "question": "What is this about?",
            "expected_keywords": ["Python", "testing"],
            "category": "answer_quality",
            "difficulty": "easy",
        }
    ]
    (tmp_path / "questions.json").write_text(json.dumps(questions))
    return tmp_path


# ---------------------------------------------------------------------------
# BenchQuestion model
# ---------------------------------------------------------------------------


class TestBenchQuestion:
    def test_minimal(self) -> None:
        q = BenchQuestion(id="q1", question="What?")
        assert q.expected_keywords == []
        assert q.category == "answer_quality"
        assert q.difficulty == "medium"

    def test_full(self) -> None:
        q = BenchQuestion(
            id="q1",
            question="What is X?",
            expected_keywords=["x", "y"],
            category="cross_document",
            difficulty="hard",
        )
        assert q.expected_keywords == ["x", "y"]
        assert q.category == "cross_document"


# ---------------------------------------------------------------------------
# load_dataset
# ---------------------------------------------------------------------------


class TestLoadDataset:
    def test_loads_valid_dataset(self, sample_dataset: Path) -> None:
        ds = load_dataset(sample_dataset)
        assert ds.name == sample_dataset.name
        assert len(ds.questions) == 1
        assert len(ds.doc_files) == 1

    def test_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nonexistent")

    def test_missing_docs(self, tmp_path: Path) -> None:
        (tmp_path / "questions.json").write_text("[]")
        with pytest.raises(FileNotFoundError, match="docs/"):
            load_dataset(tmp_path)

    def test_missing_questions(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test.md").write_text("# Test")
        with pytest.raises(FileNotFoundError, match="questions.json"):
            load_dataset(tmp_path)

    def test_empty_questions(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test.md").write_text("# Test")
        (tmp_path / "questions.json").write_text("[]")
        with pytest.raises(ValueError, match="at least one"):
            load_dataset(tmp_path)

    def test_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test.md").write_text("# Test")
        (tmp_path / "questions.json").write_text('{"not": "an array"}')
        with pytest.raises(ValueError, match="array"):
            load_dataset(tmp_path)

    def test_no_supported_docs(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test.txt").write_text("plain text")
        (tmp_path / "questions.json").write_text('[{"id":"q1","question":"Q?"}]')
        with pytest.raises(FileNotFoundError, match="No supported"):
            load_dataset(tmp_path)

    def test_finds_multiple_doc_types(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "a.md").write_text("# A")
        (tmp_path / "docs" / "b.markdown").write_text("# B")
        (tmp_path / "questions.json").write_text('[{"id":"q1","question":"Q?"}]')
        ds = load_dataset(tmp_path)
        assert len(ds.doc_files) == 2


# ---------------------------------------------------------------------------
# compute_keyword_score
# ---------------------------------------------------------------------------


class TestComputeKeywordScore:
    def test_all_keywords_found(self) -> None:
        matched, score = compute_keyword_score(
            "Python supports integers and strings",
            ["Python", "integers", "strings"],
        )
        assert score == 1.0
        assert len(matched) == 3

    def test_partial_match(self) -> None:
        matched, score = compute_keyword_score(
            "Python is great",
            ["Python", "Java", "Go"],
        )
        assert score == pytest.approx(1 / 3)
        assert matched == ["Python"]

    def test_no_match(self) -> None:
        matched, score = compute_keyword_score(
            "Nothing relevant here",
            ["Python", "Java"],
        )
        assert score == 0.0
        assert matched == []

    def test_case_insensitive(self) -> None:
        matched, score = compute_keyword_score(
            "python is GREAT",
            ["Python", "great"],
        )
        assert score == 1.0

    def test_empty_keywords(self) -> None:
        matched, score = compute_keyword_score("Any answer", [])
        assert score == 1.0

    def test_empty_answer(self) -> None:
        matched, score = compute_keyword_score("", ["keyword"])
        assert score == 0.0


# ---------------------------------------------------------------------------
# BenchResults
# ---------------------------------------------------------------------------


class TestBenchResults:
    def _make_result(self, score: float = 0.8, latency: float = 50.0, tokens: int = 200, category: str = "answer_quality") -> QuestionResult:
        return QuestionResult(
            question_id="q1",
            question="Test?",
            category=category,
            difficulty="easy",
            answer="Answer",
            expected_keywords=["x"],
            matched_keywords=["x"] if score > 0 else [],
            keyword_score=score,
            latency_ms=latency,
            token_estimate=tokens,
            sources_used=1,
            routed_ckus=1,
        )

    def test_avg_keyword_score(self) -> None:
        results = BenchResults(
            dataset_name="test",
            total_questions=2,
            compile_time_s=1.0,
            compile_doc_count=1,
            question_results=[
                self._make_result(score=1.0),
                self._make_result(score=0.5),
            ],
        )
        assert results.avg_keyword_score == pytest.approx(0.75)

    def test_avg_latency(self) -> None:
        results = BenchResults(
            dataset_name="test",
            total_questions=2,
            compile_time_s=1.0,
            compile_doc_count=1,
            question_results=[
                self._make_result(latency=100.0),
                self._make_result(latency=200.0),
            ],
        )
        assert results.avg_latency_ms == pytest.approx(150.0)

    def test_category_scores(self) -> None:
        results = BenchResults(
            dataset_name="test",
            total_questions=3,
            compile_time_s=1.0,
            compile_doc_count=1,
            question_results=[
                self._make_result(score=1.0, category="answer_quality"),
                self._make_result(score=0.5, category="answer_quality"),
                self._make_result(score=0.8, category="cross_document"),
            ],
        )
        cats = results.category_scores
        assert cats["answer_quality"] == pytest.approx(0.75)
        assert cats["cross_document"] == pytest.approx(0.8)

    def test_empty_results(self) -> None:
        results = BenchResults(
            dataset_name="test",
            total_questions=0,
            compile_time_s=0.0,
            compile_doc_count=0,
        )
        assert results.avg_keyword_score == 0.0
        assert results.avg_latency_ms == 0.0

    def test_to_dict(self) -> None:
        results = BenchResults(
            dataset_name="test",
            total_questions=1,
            compile_time_s=1.5,
            compile_doc_count=1,
            question_results=[self._make_result()],
        )
        d = results.to_dict()
        assert d["dataset"] == "test"
        assert d["compile_time_s"] == 1.5
        assert len(d["questions"]) == 1
        assert "avg_keyword_score" in d
