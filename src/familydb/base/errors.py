"""Exception types shared across FamilyDB."""

from __future__ import annotations


class FamilyDBError(Exception):
    """Base class for FamilyDB errors."""


class ToolError(FamilyDBError):
    """Raised by a tool handler. Reported to the model as an error result."""


class ToolUnavailable(ToolError):
    """The tool exists but its backing service is not configured yet."""


class MigrationError(FamilyDBError):
    """The bundled migrations and the database's record of them disagree: one applied was
    changed since, or one numbered below the newest applied was never applied."""


class ConfigError(FamilyDBError):
    """A setting is missing or contradictory, and the thing it configures cannot start."""


class AgentError(FamilyDBError):
    """The model call failed. `retryable` says whether a later attempt may succeed.

    `trouble` names a failure only an admin can fix, as the provider module read it: "credit"
    (out of credit or quota), "key" (key refused), "model" (the company lacks the model: retired
    or mistyped), "refused" (a 4xx the module cannot name, maybe a change on the company's side).
    All are told to admins (alerts.py); all but "refused" are worth asking the other company
    instead, since a request refused as sent may fail the same way anywhere.
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
