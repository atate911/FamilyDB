"""Exception types shared across FamilyDB."""

from __future__ import annotations


class FamilyDBError(Exception):
    """Base class for FamilyDB errors."""


class ToolError(FamilyDBError):
    """Raised by a tool handler. Reported to the model as an error result."""


class ToolUnavailable(ToolError):
    """The tool exists but its backing service is not configured yet."""


class ConfigError(FamilyDBError):
    """A setting is missing or contradictory, and the thing it configures cannot start."""


class AgentError(FamilyDBError):
    """The model call failed. `retryable` says whether a later attempt may succeed.

    `trouble` names a failure only an admin can fix, as the provider module read it: "credit",
    the company's account is out of credit or over its quota; "key", the company refused the
    key; "model", the company does not have the model asked for (retired, or mistyped). They are
    worth asking the other company instead, and worth telling an admin (alerts.py).
    """

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        request_id: str | None = None,
        trouble: str | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.request_id = request_id
        self.trouble = trouble
