# VibeVerse AI — Recommendation Engine & Evaluation

## 1. Hybrid Scoring Formula

Defined in `recommendation_engine/algorithms/hybrid_recommender.py`:

```text
TotalScore = 0.28 * preference_sim
           + 0.24 * content_sim
           + 0.20 * mood_sim
           + 0.14 * cross_domain_sim
           + 0.10 * feedback_boost
           + 0.04 * novelty
```

- **`preference_sim`**: Genre overlap + TF-IDF match against user's explicit genres, artists, themes, storytelling style, and energy/acoustic/pacing preferences.
- **`content_sim`**: Mean cosine similarity in combined TF-IDF + Vibe space against user's seed titles, liked items, and `"More like this"` anchors.
- **`mood_sim`**: Jaccard-normalized overlap between item mood tags and active session moods.
- **`cross_domain_sim`**: Cosine similarity inside the shared 29-dimensional cross-domain vibe vector (`18` canonical moods + `8` shared theme buckets + `3` energy/pacing states).
- **`feedback_boost`**: Sigmoid-normalized sum of learned genre/mood/artist feedback weights (`like`: `+0.35`, `save`: `+0.45`, `more_like_this`: `+0.60`, `dislike`: `-0.45`, `not_interested`: `-0.35`, `less_like_this`: `-0.55`). When `>= 5` distinct sessions have recorded feedback, item-item collaborative filtering blends in (`0.30` weight); otherwise CF remains inactive.
- **`novelty`**: Inverse genre frequency across the catalog (boosted for `underrated` items when requested).

## 2. Diversity & Language Balancing

- **MMR Diversity Re-ranking:** Iteratively selects items maximizing `(1 - λ) * score - λ * max_similarity_to_selected` (`λ = 0.22`) with a cap of 2 tracks per primary artist.
- **5 Language Modes:** `both` (interleaved ~50/50 Hindi & English target with honest notice if one pool is smaller), `hindi_only`, `english_only`, `hindi_pref_english_rec`, and `english_pref_hindi_rec`.

## 3. Evaluation Methodology (`recommendation_engine/evaluation/evaluator.py`)

- **Unsupervised Live Metrics:** Intra-List Diversity (`1 - avg pairwise cosine similarity`), Catalog Coverage, and Self-Information Novelty.
- **Supervised Ranking Metrics (`Precision@K`, `Recall@K`, `Hit Rate@K`):** Computed strictly when explicit ground-truth relevant item IDs are provided (e.g., held-out evaluation scenarios). For unlabeled live sessions, `ground_truth_available` is `false` and supervised metrics return `null` rather than fabricated scores.
