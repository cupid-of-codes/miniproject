"""Recommendation quality evaluation metrics (without fabricating ground-truth results)."""

from typing import Any, Dict, List, Optional, Set

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex


def compute_intra_list_diversity(
    index: CatalogFeatureIndex, recommended_items: List[Dict[str, Any]]
) -> float:
    """Compute average pairwise dissimilarity (1 - cosine similarity) across recommended items."""
    indices = [
        index.ext_to_idx[(item["external_id"], item["content_type"])]
        for item in recommended_items
        if (item.get("external_id"), item.get("content_type")) in index.ext_to_idx
    ]
    if len(indices) < 2:
        return 0.0
    vecs = index.combined_matrix[indices]
    sim_matrix = cosine_similarity(vecs)
    n = len(indices)
    upper_indices = np.triu_indices(n, k=1)
    avg_sim = float(np.mean(sim_matrix[upper_indices]))
    return round(max(0.0, min(1.0, 1.0 - avg_sim)), 4)


def compute_catalog_coverage(
    recommended_batches: List[List[Dict[str, Any]]], total_catalog_size: int
) -> float:
    """Fraction of the catalog surfaced across recommendation batches."""
    if total_catalog_size <= 0:
        return 0.0
    seen = {
        (item.get("external_id"), item.get("content_type"))
        for batch in recommended_batches
        for item in batch
        if item.get("external_id")
    }
    return round(len(seen) / total_catalog_size, 4)


def compute_novelty(
    index: CatalogFeatureIndex, recommended_items: List[Dict[str, Any]]
) -> float:
    """Compute self-information novelty based on inverse genre frequency in the catalog."""
    if not recommended_items or not index.items:
        return 0.0
    genre_counts: Dict[str, int] = {}
    for item in index.items:
        for g in item.get("genres", []):
            genre_counts[g.lower()] = genre_counts.get(g.lower(), 0) + 1
    total_items = len(index.items)

    novelties = []
    for item in recommended_items:
        genres = [g.lower() for g in item.get("genres", [])]
        if not genres:
            continue
        item_nov = np.mean([-np.log2(genre_counts.get(g, 1) / total_items) for g in genres])
        novelties.append(float(item_nov))
    return round(float(np.mean(novelties)), 4) if novelties else 0.0


def evaluate_ranking_against_ground_truth(
    recommended_external_ids: List[str],
    relevant_external_ids: Optional[Set[str]],
    k: int = 10,
) -> Dict[str, Any]:
    """Compute Precision@K, Recall@K, and Hit Rate@K ONLY when real ground-truth labels exist."""
    if not relevant_external_ids:
        return {
            "precision_at_k": None,
            "recall_at_k": None,
            "hit_rate_at_k": None,
            "ground_truth_available": False,
            "note": "Ground-truth relevance labels are unavailable for this session; supervised ranking metrics are omitted rather than fabricated.",
        }

    top_k = recommended_external_ids[:k]
    hits = sum(1 for eid in top_k if eid in relevant_external_ids)
    precision = hits / max(1, len(top_k))
    recall = hits / max(1, len(relevant_external_ids))
    hit_rate = 1.0 if hits > 0 else 0.0
    return {
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4),
        "hit_rate_at_k": round(hit_rate, 4),
        "ground_truth_available": True,
        "k": k,
        "hits": hits,
    }
