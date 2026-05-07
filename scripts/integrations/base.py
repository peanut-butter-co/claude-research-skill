from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Source:
    url: str
    title: str
    snippet: str | None = None
    tier: str = "C"
    integration: str = ""


class BaseIntegration(ABC):
    integration_id: str = ""

    @abstractmethod
    def enrich(self, query: str) -> list[Source]:
        ...

    def is_configured(self, env: dict) -> bool:
        return True
