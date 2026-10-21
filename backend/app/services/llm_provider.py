"""LLM extension point. No provider is configured in this phase; the NullProvider never answers."""
from typing import Protocol

LLM_NOT_IMPLEMENTED_NOTE = "LLM explanation is not implemented in this phase"


class LLMProvider(Protocol):
    """Interface a future provider must implement. It may only rephrase supplied facts."""

    name: str

    def is_available(self) -> bool:
        """Whether the provider can currently answer."""
        ...

    def explain(self, facts: list[str]) -> str | None:
        """Return a rephrasing of the given facts, or None."""
        ...


class NullProvider:
    """Provider that is never available and never produces text."""

    name = "none"

    def is_available(self) -> bool:
        """Always False."""
        return False

    def explain(self, facts: list[str]) -> str | None:
        """Always None."""
        return None


def get_provider() -> LLMProvider:
    """The configured provider (always the NullProvider in this phase)."""
    return NullProvider()
