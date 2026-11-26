"""TF-IDF vectorization, shared cross-domain vibe vectors, cosine similarity, and K-Means clustering."""

from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from recommendation_engine.preprocessing.text_cleaner import CANONICAL_MOODS, clean_text

SHARED_THEME_BUCKETS: Dict[str, Tuple[str, ...]] = {
    "atmospheric_noir": ("atmospheric", "noir", "rain", "midnight", "shadow", "neon", "mist", "fog"),
    "mystery_investigation": ("mystery", "investigation", "detective", "twist", "secret", "conspiracy", "crime"),
    "romance_intimacy": ("love", "romance", "intimate", "tender", "heartbreak", "longing", "affection"),
    "sci_fi_cosmic": ("sci-fi", "space", "time", "multiverse", "cyber", "ai", "future", "dimension"),
    "comfort_warmth": ("comfort", "warm", "friendship", "family", "simple", "road trip", "sunny", "cozy"),
    "rebellion_intensity": ("rebellion", "fierce", "grit", "power", "intensity", "revolution", "pressure"),
    "nostalgia_memory": ("nostalgia", "memory", "childhood", "retro", "vintage", "1990s", "1980s", "past"),
    "indie_poetic": ("indie", "poetic", "acoustic", "minimalist", "art", "folk", "sufi", "storytelling"),
}


class CatalogFeatureIndex:
    """In-memory vectorized representation of the entertainment catalog for fast ML scoring."""

    def __init__(self, items: List[Dict[str, Any]]) -> None:
        self.items: List[Dict[str, Any]] = items
        self.id_to_idx: Dict[int, int] = {
            int(item["id"]): idx for idx, item in enumerate(items) if item.get("id") is not None
        }
        self.ext_to_idx: Dict[Tuple[str, str], int] = {
            (str(item["external_id"]), str(item["content_type"])): idx
            for idx, item in enumerate(items)
            if item.get("external_id")
        }

        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=2500,
            sublinear_tf=True,
        )
        self.tfidf_matrix = self._build_tfidf_matrix()
        self.vibe_matrix = self._build_shared_vibe_matrix()
        self.combined_matrix = self._build_combined_matrix()
        self.cluster_labels = self._fit_kmeans_clusters()

    def _item_text_document(self, item: Dict[str, Any]) -> str:
        extra = item.get("extra_metadata") or {}
        talent = " ".join(
            str(extra.get(k, "")) for k in ("artist", "album", "director", "creator", "storytelling_style")
        )
        parts = [
            item.get("title", ""),
            " ".join(item.get("genres", []) * 2),
            " ".join(item.get("mood_tags", []) * 2),
            " ".join(item.get("themes", []) * 2),
            talent,
            item.get("description", ""),
        ]
        return clean_text(" ".join(parts))

    def _build_tfidf_matrix(self) -> np.ndarray:
        if not self.items:
            return np.zeros((0, 1), dtype=float)
        docs = [self._item_text_document(item) or "entertainment" for item in self.items]
        return self.tfidf_vectorizer.fit_transform(docs).toarray()

    def _item_vibe_vector(self, item: Dict[str, Any]) -> np.ndarray:
        """Build cross-domain shared preference vector: moods + theme buckets + energy/pacing."""
        moods_set = {m.lower() for m in item.get("mood_tags", [])}
        mood_vec = [1.0 if m.lower() in moods_set else 0.0 for m in CANONICAL_MOODS]

        text_blob = " ".join(
            [
                " ".join(item.get("genres", [])),
                " ".join(item.get("themes", [])),
                item.get("description", ""),
                str((item.get("extra_metadata") or {}).get("storytelling_style", "")),
            ]
        ).lower()

        theme_vec = []
        for keywords in SHARED_THEME_BUCKETS.values():
            hits = sum(1.0 for kw in keywords if kw in text_blob)
            theme_vec.append(min(1.0, hits / 2.0))

        extra = item.get("extra_metadata") or {}
        energy_raw = str(
            extra.get("energy")
            or (extra.get("music_analysis") or {}).get("inferred_energy")
            or extra.get("pacing")
            or "balanced"
        ).lower()

        is_calm = 1.0 if energy_raw in {"calm", "slow_burn"} else 0.0
        is_medium = 1.0 if energy_raw in {"medium", "balanced"} else 0.0
        is_high = 1.0 if energy_raw in {"high", "fast_paced"} else 0.0

        vec = np.array(mood_vec + theme_vec + [is_calm, is_medium, is_high], dtype=float)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _build_shared_vibe_matrix(self) -> np.ndarray:
        if not self.items:
            return np.zeros((0, len(CANONICAL_MOODS) + len(SHARED_THEME_BUCKETS) + 3), dtype=float)
        return np.vstack([self._item_vibe_vector(item) for item in self.items])

    def _build_combined_matrix(self) -> np.ndarray:
        if not self.items:
            return np.zeros((0, 1), dtype=float)
        combined = np.hstack([self.tfidf_matrix * 0.65, self.vibe_matrix * 0.75])
        norms = np.linalg.norm(combined, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return combined / norms

    def _fit_kmeans_clusters(self) -> List[int]:
        n_items = len(self.items)
        if n_items == 0:
            return []
        if n_items < 4:
            return [0] * n_items
        n_clusters = min(8, max(2, n_items // 12))
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(self.combined_matrix)
        return [int(label) for label in labels]

    def query_tfidf_similarity(self, query_text: str) -> np.ndarray:
        """Compute cosine similarity between a free-text query and all catalog items."""
        if not self.items:
            return np.array([], dtype=float)
        cleaned = clean_text(query_text)
        if not cleaned:
            return np.zeros(len(self.items), dtype=float)
        q_vec = self.tfidf_vectorizer.transform([cleaned]).toarray()
        return cosine_similarity(q_vec, self.tfidf_matrix)[0]

    def item_similarity_vector(self, seed_indices: List[int]) -> np.ndarray:
        """Compute max/mean cosine similarity from a set of seed items to the entire catalog."""
        if not self.items or not seed_indices:
            return np.zeros(len(self.items), dtype=float)
        valid_indices = [idx for idx in seed_indices if 0 <= idx < len(self.items)]
        if not valid_indices:
            return np.zeros(len(self.items), dtype=float)
        seed_vecs = self.combined_matrix[valid_indices]
        sims = cosine_similarity(seed_vecs, self.combined_matrix)
        return np.mean(sims, axis=0)

    def cross_domain_vibe_similarity(self, seed_indices: List[int]) -> np.ndarray:
        """Compute similarity specifically in the shared cross-domain vibe space."""
        if not self.items or not seed_indices:
            return np.zeros(len(self.items), dtype=float)
        valid_indices = [idx for idx in seed_indices if 0 <= idx < len(self.items)]
        if not valid_indices:
            return np.zeros(len(self.items), dtype=float)
        seed_vecs = self.vibe_matrix[valid_indices]
        sims = cosine_similarity(seed_vecs, self.vibe_matrix)
        return np.mean(sims, axis=0)
