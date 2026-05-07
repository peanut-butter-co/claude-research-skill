import requests

from scripts.integrations.base import BaseIntegration, Source


class GooglePlacesIntegration(BaseIntegration):
    integration_id = "google_places"
    _API_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    def is_configured(self, env: dict) -> bool:
        return bool(env.get("GOOGLE_PLACES_KEY"))

    def enrich(self, query: str, env: dict | None = None) -> list[Source]:
        if env is None:
            env = {}
        if not self.is_configured(env):
            return []

        key = env["GOOGLE_PLACES_KEY"]
        try:
            response = requests.get(
                self._API_URL,
                params={"query": query, "key": key},
                timeout=10,
            )
            if response.status_code != 200:
                return []
            data = response.json()
            results = data["results"]
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            KeyError,
        ):
            return []

        sources: list[Source] = []
        for result in results[:10]:
            place_id = result.get("place_id", "")
            sources.append(
                Source(
                    url=f"https://maps.google.com/maps/place/?q=place_id:{place_id}",
                    title=result.get("name", ""),
                    snippet=result.get("formatted_address", ""),
                    tier="B",
                    integration="google_places",
                )
            )
        return sources


integration = GooglePlacesIntegration()
