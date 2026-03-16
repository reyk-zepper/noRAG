"""SQLite-backed knowledge map for fast entity/topic/keyword lookup across all CKUs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from norag.models.cku import CKU
from norag.utils import source_to_id as _source_to_id_util


class KnowledgeMap:
    """SQLite-backed index over all CKUs for fast lookup."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        """Create the knowledge map schema."""
        cur = self._conn.cursor()

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS ckus (
                id          TEXT PRIMARY KEY,
                source      TEXT NOT NULL,
                compiled    TEXT NOT NULL,
                doc_summary TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS entities (
                id      TEXT NOT NULL,
                cku_id  TEXT NOT NULL REFERENCES ckus(id) ON DELETE CASCADE,
                name    TEXT NOT NULL,
                type    TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (id, cku_id)
            );
            CREATE INDEX IF NOT EXISTS idx_entities_cku_id ON entities(cku_id);
            CREATE INDEX IF NOT EXISTS idx_entities_name   ON entities(name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS entity_relations (
                entity_id     TEXT NOT NULL,
                cku_id        TEXT NOT NULL,
                target        TEXT NOT NULL,
                relation_type TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (entity_id, cku_id) REFERENCES entities(id, cku_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_entity_relations_entity
                ON entity_relations(entity_id, cku_id);

            CREATE TABLE IF NOT EXISTS facts (
                id     TEXT NOT NULL,
                cku_id TEXT NOT NULL REFERENCES ckus(id) ON DELETE CASCADE,
                claim  TEXT NOT NULL,
                PRIMARY KEY (id, cku_id)
            );
            CREATE INDEX IF NOT EXISTS idx_facts_cku_id ON facts(cku_id);

            CREATE TABLE IF NOT EXISTS topics (
                cku_id TEXT NOT NULL REFERENCES ckus(id) ON DELETE CASCADE,
                topic  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_topics_cku_id ON topics(cku_id);
            CREATE INDEX IF NOT EXISTS idx_topics_topic  ON topics(topic COLLATE NOCASE);
        """)

        # FTS5 virtual table for full-text search on fact claims.
        # Standalone (not a content table) so we can DELETE by cku_id freely.
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
            USING fts5(
                claim,
                cku_id UNINDEXED,
                fact_id UNINDEXED
            )
        """)

        self._conn.commit()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_cku(self, cku: CKU) -> None:
        """Index a CKU into the knowledge map. Replaces existing entry for same source."""
        cku_id = self._source_to_id(cku.meta.source)
        cur = self._conn.cursor()

        # 1. Remove all existing data for this cku_id (CASCADE handles children).
        #    FTS table is a content table so we sync it manually.
        cur.execute(
            "DELETE FROM facts_fts WHERE cku_id = ?",
            (cku_id,),
        )
        cur.execute("DELETE FROM ckus WHERE id = ?", (cku_id,))

        # 2. Insert CKU header row.
        cur.execute(
            "INSERT INTO ckus (id, source, compiled, doc_summary) VALUES (?, ?, ?, ?)",
            (
                cku_id,
                cku.meta.source,
                cku.meta.compiled.isoformat(),
                cku.summaries.document,
            ),
        )

        # 3. Insert entities and their relations.
        for entity in cku.entities:
            cur.execute(
                "INSERT OR REPLACE INTO entities (id, cku_id, name, type) VALUES (?, ?, ?, ?)",
                (entity.id, cku_id, entity.name, entity.type),
            )
            for rel in entity.relations:
                cur.execute(
                    "INSERT INTO entity_relations (entity_id, cku_id, target, relation_type)"
                    " VALUES (?, ?, ?, ?)",
                    (entity.id, cku_id, rel.target, rel.type),
                )

        # 4. Insert facts and keep FTS in sync.
        for fact in cku.facts:
            cur.execute(
                "INSERT OR REPLACE INTO facts (id, cku_id, claim) VALUES (?, ?, ?)",
                (fact.id, cku_id, fact.claim),
            )
            cur.execute(
                "INSERT INTO facts_fts (claim, cku_id, fact_id) VALUES (?, ?, ?)",
                (fact.claim, cku_id, fact.id),
            )

        # 5. Extract topics from entity types and section summary titles.
        topics: set[str] = set()
        for entity in cku.entities:
            if entity.type:
                topics.add(entity.type.lower())
        for section in cku.summaries.sections:
            if section.title:
                topics.add(section.title.lower())
        for topic in topics:
            cur.execute(
                "INSERT INTO topics (cku_id, topic) VALUES (?, ?)",
                (cku_id, topic),
            )

        self._conn.commit()

    # ------------------------------------------------------------------
    # Lookup methods
    # ------------------------------------------------------------------

    def find_by_entity(self, entity_name: str) -> list[str]:
        """Find CKU IDs that contain a given entity (case-insensitive partial match)."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT DISTINCT cku_id FROM entities"
            " WHERE name LIKE ? COLLATE NOCASE",
            (f"%{entity_name}%",),
        )
        return [row["cku_id"] for row in cur.fetchall()]

    def find_by_topic(self, topic: str) -> list[str]:
        """Find CKU IDs related to a topic (case-insensitive partial match)."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT DISTINCT cku_id FROM topics"
            " WHERE topic LIKE ? COLLATE NOCASE",
            (f"%{topic}%",),
        )
        return [row["cku_id"] for row in cur.fetchall()]

    def find_by_keywords(self, keywords: list[str]) -> list[str]:
        """Full-text search across fact claims. Returns CKU IDs ranked by relevance."""
        if not keywords:
            return []

        # Build an FTS5 query: join keywords with AND so all must appear.
        # Each keyword is wrapped in double quotes to treat it as a phrase.
        fts_query = " AND ".join(f'"{kw}"' for kw in keywords)

        cur = self._conn.cursor()
        try:
            cur.execute(
                "SELECT cku_id, COUNT(*) AS hits"
                " FROM facts_fts"
                " WHERE facts_fts MATCH ?"
                " GROUP BY cku_id"
                " ORDER BY hits DESC",
                (fts_query,),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            # Fall back to OR if AND yields no results / syntax error.
            fts_query_or = " OR ".join(f'"{kw}"' for kw in keywords)
            cur.execute(
                "SELECT cku_id, COUNT(*) AS hits"
                " FROM facts_fts"
                " WHERE facts_fts MATCH ?"
                " GROUP BY cku_id"
                " ORDER BY hits DESC",
                (fts_query_or,),
            )
            rows = cur.fetchall()

        return [row["cku_id"] for row in rows]

    def get_entity_relations(self, entity_name: str) -> list[dict]:
        """Get all relations for an entity across all CKUs."""
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT
                e.id        AS entity_id,
                e.name      AS entity_name,
                e.type      AS entity_type,
                er.target,
                er.relation_type,
                er.cku_id
            FROM entities e
            JOIN entity_relations er
                ON er.entity_id = e.id AND er.cku_id = e.cku_id
            WHERE e.name LIKE ? COLLATE NOCASE
            ORDER BY e.cku_id, er.relation_type
            """,
            (f"%{entity_name}%",),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_all_entities(self) -> list[dict]:
        """List all indexed entities with their types and CKU IDs."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, name, type, cku_id FROM entities ORDER BY name COLLATE NOCASE"
        )
        return [dict(row) for row in cur.fetchall()]

    def get_stats(self) -> dict:
        """Return stats: total CKUs, entities, facts, etc."""
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM ckus")
        total_ckus = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM entities")
        total_entities = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM facts")
        total_facts = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM entity_relations")
        total_relations = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(DISTINCT topic) AS n FROM topics")
        total_topics = cur.fetchone()["n"]

        return {
            "total_ckus": total_ckus,
            "total_entities": total_entities,
            "total_facts": total_facts,
            "total_relations": total_relations,
            "total_topics": total_topics,
        }

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _source_to_id(source: str) -> str:
        """Convert source path to a unique, safe CKU ID."""
        return _source_to_id_util(source)
