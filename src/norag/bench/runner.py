"""Benchmark runner — orchestrates compile + query + measure."""

from __future__ import annotations

import time
from pathlib import Path

from norag.bench.dataset import BenchDataset
from norag.bench.metrics import BenchResults, QuestionResult, compute_keyword_score
from norag.compiler.engine import CompilerEngine
from norag.config import Config
from norag.query.engine import QueryEngine


class BenchRunner:
    """Runs a benchmark dataset against noRAG."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.compiler = CompilerEngine(config)
        self.query_engine = QueryEngine(config)

    def run(self, dataset: BenchDataset, force_compile: bool = True) -> BenchResults:
        """Run the full benchmark: compile docs, then query each question.

        Args:
            dataset: The loaded benchmark dataset.
            force_compile: If True, recompile all docs even if up-to-date.

        Returns:
            Aggregated benchmark results.
        """
        # Phase 1: Compile all documents
        compile_start = time.perf_counter()
        compile_result = self.compiler.compile(dataset.docs_dir, force=force_compile)
        compile_time = time.perf_counter() - compile_start

        # Phase 2: Query each question and measure
        question_results: list[QuestionResult] = []

        for q in dataset.questions:
            query_start = time.perf_counter()
            result = self.query_engine.query(q.question)
            query_time_ms = (time.perf_counter() - query_start) * 1000

            matched, score = compute_keyword_score(result.answer, q.expected_keywords)

            question_results.append(
                QuestionResult(
                    question_id=q.id,
                    question=q.question,
                    category=q.category,
                    difficulty=q.difficulty,
                    answer=result.answer,
                    expected_keywords=q.expected_keywords,
                    matched_keywords=matched,
                    keyword_score=score,
                    latency_ms=query_time_ms,
                    token_estimate=result.context.token_estimate,
                    sources_used=len(result.context.sources),
                    routed_ckus=len(result.routed_ckus),
                )
            )

        return BenchResults(
            dataset_name=dataset.name,
            total_questions=len(dataset.questions),
            compile_time_s=compile_time,
            compile_doc_count=len(dataset.doc_files),
            question_results=question_results,
        )
