"""CLI script to preprocess and validate raw datasets into data/processed/."""

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import get_settings
from backend.core.logging_config import setup_logging
from recommendation_engine.preprocessing.dataset_loader import load_all_datasets


def preprocess_and_save(include_external: bool = False) -> Path:
    """Clean, normalize, and write catalog JSON to data/processed/normalized_catalog.json."""
    settings = get_settings()
    logger = setup_logging(settings.log_level)

    items, summaries = load_all_datasets(include_external=include_external)
    processed_dir = settings.resolve_path(settings.processed_data_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "normalized_catalog.json"

    payload = {
        "total_items": len(items),
        "by_type": dict(Counter(item["content_type"] for item in items)),
        "by_language": dict(Counter(item["language"] for item in items)),
        "datasets": [
            {
                **s,
                "retrieved_at": s["retrieved_at"].isoformat() if s.get("retrieved_at") else None,
            }
            for s in summaries
        ],
        "items": items,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Preprocessed %d items into %s", len(items), out_path)
    print(f"Preprocessed {len(items)} items -> {out_path}")
    print(f"By type: {payload['by_type']}")
    print(f"By language: {payload['by_language']}")
    return out_path


if __name__ == "__main__":
    use_external = "--external" in sys.argv
    preprocess_and_save(include_external=use_external)
