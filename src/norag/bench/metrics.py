"""Benchmark metrics — measures quality and performance of noRAG responses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuestionResult:
    """Result of benchmarking a single question."""

    question_id: str
    question: str
    category: str
    difficulty: str
    answer: str
    expected_keywords: list[str]
    matched_keywords: list[str]
    keyword_score: float  # 0.0 - 1.0
    latency_ms: float  # query time in milliseconds
    token_estimate: int  # tokens used in context
    sources_used: int
    routed_ckus: int


@dataclass
class BenchResults:
    """Aggregated benchmark results."""

    dataset_name: str
    total_questions: int
    compile_time_s: float
    compile_doc_count: int
    question_results: list[QuestionResult] = field(default_factory=list)

    @property
    def avg_keyword_score(self) -> float:
        if not self.question_results:
            return 0.0
        return sum(r.keyword_score for r in self.question_results) / len(self.question_results)

    @property
    def avg_latency_ms(self) -> float:
        if not self.question_results:
            return 0.0
        return sum(r.latency_ms for r in self.question_results) / len(self.question_results)

    @property
    def avg_tokens(self) -> float:
        if not self.question_results:
            return 0.0
        return sum(r.token_estimate for r in self.question_results) / len(self.question_results)

    @property
    def category_scores(self) -> dict[str, float]:
        """Average keyword score per category."""
        cats: dict[str, list[float]] = {}
        for r in self.question_results:
            cats.setdefault(r.category, []).append(r.keyword_score)
        return {cat: sum(scores) / len(scores) for cat, scores in cats.items()}

    def to_dict(self) -> dict:
        """Serialize results to a JSON-compatible dict."""
        return {
            "dataset": self.dataset_name,
            "total_questions": self.total_questions,
            "compile_time_s": round(self.compile_time_s, 2),
            "compile_doc_count": self.compile_doc_count,
            "avg_keyword_score": round(self.avg_keyword_score, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_tokens": round(self.avg_tokens, 1),
            "category_scores": {k: round(v, 3) for k, v in self.category_scores.items()},
            "questions": [
                {
                    "id": r.question_id,
                    "question": r.question,
                    "category": r.category,
                    "keyword_score": round(r.keyword_score, 3),
                    "latency_ms": round(r.latency_ms, 1),
                    "token_estimate": r.token_estimate,
                    "matched_keywords": r.matched_keywords,
                    "expected_keywords": r.expected_keywords,
                }
                for r in self.question_results
            ],
        }


def compute_keyword_score(answer: str, expected_keywords: list[str]) -> tuple[list[str], float]:
    """Compute keyword match score.

    Returns (matched_keywords, score) where score is 0.0-1.0.
    """
    if not expected_keywords:
        return [], 1.0  # no expectations = pass

    answer_lower = answer.lower()
    matched = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    score = len(matched) / len(expected_keywords)
    return matched, score
