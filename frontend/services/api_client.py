"""Complete HTTP client for Streamlit -> FastAPI communication."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)


class APIClientError(Exception):
    """User-friendly API communication error."""


class VibeVerseAPIClient:
    """Typed REST client wrapper with safe timeout and error handling."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 15.0) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        cleaned_params = (
            {k: v for k, v in params.items() if v not in (None, "", "All")}
            if params
            else None
        )
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method=method, url=url, params=cleaned_params, json=json_body
                )
        except httpx.TimeoutException as exc:
            raise APIClientError(
                "The VibeVerse backend took too long to respond. Please retry in a moment."
            ) from exc
        except httpx.RequestError as exc:
            raise APIClientError(
                f"Cannot reach the VibeVerse FastAPI backend at {self.base_url}. "
                "Please ensure the FastAPI server is running."
            ) from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
                detail = payload.get("detail") or "Request failed."
            except ValueError:
                detail = f"Backend returned status {response.status_code}."
            raise APIClientError(detail)

        try:
            return response.json()
        except ValueError as exc:
            raise APIClientError("Received an invalid response format from the backend.") from exc

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def get_catalog_metadata(self) -> Dict[str, Any]:
        return self._request("GET", "/api/catalog/metadata")

    def get_preferences(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/preferences/{session_id}")

    def update_preferences(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/api/preferences/{session_id}", json_body=payload)

    def reset_preferences(self, session_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/preferences/{session_id}/reset")

    def search_domain(self, domain: str, **filters: Any) -> Dict[str, Any]:
        endpoint = {
            "song": "/api/music/search",
            "movie": "/api/movies/search",
            "series": "/api/series/search",
            "all": "/api/search",
        }.get(domain, "/api/search")
        return self._request("GET", endpoint, params=filters)

    def recommend_domain(
        self,
        domain: str,
        session_id: str,
        limit: int = 10,
        category: Optional[str] = None,
        language_mode_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        endpoint = {
            "song": "/api/music/recommendations",
            "movie": "/api/movies/recommendations",
            "series": "/api/series/recommendations",
        }[domain]
        body = {
            "session_id": session_id,
            "limit": limit,
            "category": None if category in (None, "All") else category,
            "language_mode_override": language_mode_override,
        }
        return self._request("POST", endpoint, json_body=body)

    def get_trending(self) -> Dict[str, Any]:
        return self._request("GET", "/api/trending")

    def cross_domain(
        self,
        session_id: str,
        pathway: str,
        seed_titles: Optional[List[str]] = None,
        limit: int = 8,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/recommendations/cross-domain",
            json_body={
                "session_id": session_id,
                "pathway": pathway,
                "seed_titles": seed_titles or None,
                "limit": limit,
            },
        )

    def discovery_chain(
        self, session_id: str, seed_titles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/recommendations/chain",
            json_body={"session_id": session_id, "pathway": "music_to_movies", "seed_titles": seed_titles or None},
        )

    def unexpected_vibe(self, session_id: str, limit: int = 6) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/recommendations/unexpected",
            json_body={"session_id": session_id, "limit": limit},
        )

    def mood_match(
        self,
        session_id: str,
        moods: List[str],
        mood_text: str = "",
        language_mode: Optional[str] = None,
        limit_per_domain: int = 5,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/recommendations/mood",
            json_body={
                "session_id": session_id,
                "moods": moods,
                "mood_text": mood_text,
                "language_mode": language_mode,
                "limit_per_domain": limit_per_domain,
            },
        )

    def get_personality(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/personality/{session_id}")

    def analyze_personality(self, session_id: str) -> Dict[str, Any]:
        return self._request(
            "POST", "/api/personality/analyze", json_body={"session_id": session_id}
        )

    def submit_feedback(
        self, session_id: str, content_id: int, feedback_type: str
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/feedback",
            json_body={
                "session_id": session_id,
                "content_id": content_id,
                "feedback_type": feedback_type,
            },
        )

    def get_feedback(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/feedback/{session_id}")

    def save_item(self, session_id: str, content_id: int) -> Dict[str, Any]:
        return self._request(
            "POST", "/api/saved", json_body={"session_id": session_id, "content_id": content_id}
        )

    def get_saved(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/saved/{session_id}")

    def delete_saved(self, session_id: str, content_id: int) -> Dict[str, Any]:
        return self._request("DELETE", f"/api/saved/{session_id}/{content_id}")

    def get_trends_analytics(self) -> Dict[str, Any]:
        return self._request("GET", "/api/analytics/trends")

    def get_preference_analytics(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/analytics/preferences/{session_id}")
