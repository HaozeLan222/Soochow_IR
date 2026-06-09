# Tutor Search Evaluation Set

This directory contains a task-oriented evaluation set for the Soochow University tutor vertical search system.

The set is built from:

```text
Soochow_IR/data/processed/handoff/handoff_teachers.clean.jsonl
```

It is designed to evaluate the planned optimized IR features:

- exact and fuzzy teacher-name matching
- research-direction retrieval
- paper/achievement-oriented retrieval
- college alias normalization and college filtering
- title/stage constraints
- colloquial query normalization
- soft preference ranking, such as publication-rich or young-teacher queries

## Files

```text
queries.jsonl
qrels.jsonl
qrels_by_query.md
```

`queries.jsonl` contains 48 evaluation queries, grouped into 8 categories with 6 queries each.

`qrels.jsonl` contains pool-based relevance judgments for these queries.

`qrels_by_query.md` is a human-readable grouped preview showing which teachers are judged relevant for each query.

## Query Categories

| Category | Count | Purpose |
|---|---:|---|
| `exact_name` | 6 | Test exact teacher-name lookup. |
| `fuzzy_name` | 6 | Test typo/near-match teacher-name retrieval. |
| `research_direction` | 6 | Test single research direction retrieval. |
| `paper_achievement` | 6 | Test whether papers/achievements fields are weighted properly. |
| `college_research` | 6 | Test college constraint plus research direction. |
| `title_research` | 6 | Test title/stage constraint plus research direction. |
| `soft_preference` | 6 | Test ranking preferences such as publication-rich or young teacher. |
| `colloquial_compound` | 6 | Test natural user-style compound queries. |

## Relevance Scale

The relevance judgments use a 0-3 scale. Documents with relevance 0 are omitted.

```text
3 = Highly relevant. The teacher clearly satisfies the main query intent and hard constraints.
2 = Relevant. The teacher satisfies the main topic, but one condition is weaker or indirect.
1 = Weakly relevant. The teacher is related to the broader topic, but not an ideal answer.
```

For binary metrics such as Precision@5 and MRR, use `relevance >= 2` as relevant by default.

For graded metrics such as NDCG@5 or NDCG@10, use the raw `relevance` score.

## Notes On Soft Conditions

Some real user conditions are not explicit structured fields in the source data.

- `publication_rich`: approximated by the presence, length, and specificity of `papers`, as well as clear venue/achievement terms such as ACL, CCF-A, Nature, SCI, or named journal/conference records.
- `young_teacher`: approximated conservatively by visible career-stage signals such as `讲师`, `副教授`, `副研究员`, recent research topics, or profile text. It is not an age judgment.
- college aliases such as `计算机学院`, `数学学院`, `物理学院`, and `纳米学院` should be normalized to the full college names before filtering.

The qrels are pool-based and intentionally not exhaustive. They are suitable for comparing the same query set across baseline and optimized systems, especially with Precision@5, MRR, and NDCG@5.

## Suggested Evaluation

Run the same query set on each system version:

```text
V0 Baseline BM25
V1 Field-aware BM25
V2 Adaptive Hybrid
V3 Semantic Enhanced, optional
```

Report both overall metrics and per-category metrics:

```text
Precision@5
MRR
NDCG@5
average latency
```

The most important categories for proving the optimized system are:

- `fuzzy_name`
- `college_research`
- `paper_achievement`
- `soft_preference`
- `colloquial_compound`
