"""Google Calendar through the official client: one family account, one shared calendar."""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from familydb.config import Settings
from familydb.errors import ToolError, ToolUnavailable

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]
REAUTH = "Google credentials are expired or revoked; run `familydb google auth` again"


@dataclass(frozen=True)
class CalendarEvent:
    """One event. For all-day events `start` and `end` are dates and `end` is exclusive."""

    id: str
    title: str
    start: datetime | date
    end: datetime | date
    all_day: bool
    location: str | None = None
    description: str | None = None
    status: str = "confirmed"
    link: str | None = None
    # Whether it takes the time up. Google calls this transparency: an event marked "free",
    # like a birthday, is on the calendar without keeping anybody from doing something.
    busy: bool = True

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "all_day": self.all_day,
            "location": self.location,
            "description": self.description,
            "status": self.status,
            "link": self.link,
            "busy": self.busy,
        }


class CalendarAPI(Protocol):
    """What the tools need from a calendar. `GoogleCalendar` implements it; tests fake it."""

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    def get_event(self, event_id: str) -> CalendarEvent | None: ...

    def insert_event(
        self,
        *,
        title: str,
        start: datetime | date,
        end: datetime | date,
        all_day: bool,
        location: str | None,
        description: str | None,
        event_id: str | None = None,
    ) -> CalendarEvent: ...

    def patch_event(self, event_id: str, **changes: Any) -> CalendarEvent: ...

    def delete_event(self, event_id: str) -> None: ...


def parse_event(item: dict[str, Any], tz: ZoneInfo) -> CalendarEvent:
    """A Google event resource to our shape, with times in the family zone."""
    start_raw = item.get("start") or {}
    end_raw = item.get("end") or {}
    if "date" in start_raw:
        start: datetime | date = date.fromisoformat(start_raw["date"])
        end: datetime | date = date.fromisoformat(end_raw.get("date", start_raw["date"]))
        all_day = True
    else:
        start = datetime.fromisoformat(start_raw["dateTime"]).astimezone(tz)
        end = datetime.fromisoformat(end_raw.get("dateTime", start_raw["dateTime"])).astimezone(tz)
        all_day = False
    return CalendarEvent(
        id=item.get("id", ""),
        title=item.get("summary") or "(no title)",
        start=start,
        end=end,
        all_day=all_day,
        location=item.get("location"),
        description=item.get("description"),
        status=item.get("status", "confirmed"),
        link=item.get("htmlLink"),
        busy=item.get("transparency", "opaque") != "transparent"
        and item.get("status") != "cancelled",
    )


def event_body(
    *,
    tz: ZoneInfo,
    title: str | None = None,
    start: datetime | date | None = None,
    end: datetime | date | None = None,
    all_day: bool | None = None,
    location: str | None = None,
    description: str | None = None,
    status: str | None = None,
    clear_other_time_key: bool = False,
) -> dict[str, Any]:
    """The request body for insert or patch. Times come as a set: start, end and all_day.

    Patches merge into the existing event, so switching between timed and all-day must null
    the key the event no longer uses (`clear_other_time_key`).
    """
    body: dict[str, Any] = {}
    if title is not None:
        body["summary"] = title
    if location is not None:
        body["location"] = location
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status
    if start is not None and end is not None:
        if all_day:
            body["start"] = {"date": start.isoformat()}
            body["end"] = {"date": end.isoformat()}
            if clear_other_time_key:
                for key in ("start", "end"):
                    body[key].update({"dateTime": None, "timeZone": None})
        else:
            body["start"] = {"dateTime": start.isoformat(), "timeZone": tz.key}
            body["end"] = {"dateTime": end.isoformat(), "timeZone": tz.key}
            if clear_other_time_key:
                for key in ("start", "end"):
                    body[key]["date"] = None
    return body


def build_service(creds: Any) -> Any:
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def load_credentials(token_path: Path) -> Any:
    """Credentials from the saved token, refreshed and re-saved when needed."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not token_path.exists():
        raise ToolUnavailable(f"no Google token at {token_path}; run `familydb google auth`")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if not (creds.expired and creds.refresh_token):
            raise ToolUnavailable(REAUTH)
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise ToolUnavailable(REAUTH) from exc
        save_token(token_path, creds.to_json())
    return creds


def save_token(token_path: Path, text: str) -> None:
    """Write the token owner-only, and whole: a half-written token is a lost calendar."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = token_path.with_name(token_path.name + ".new")
    handle = os.open(fresh, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    os.chmod(fresh, 0o600)  # in case an older file of that name was there with other rights
    os.replace(fresh, token_path)


def run_auth_flow(client_secrets: Path, token_path: Path) -> Any:
    """The one-time browser sign-in on a laptop. Saves the token for the server."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    creds = flow.run_local_server(port=0)
    save_token(token_path, creds.to_json())
    return creds


# Connecting from the web page, on a server with no browser of its own. Google sends the browser
# back to this address after consent. Nothing answers there, so the browser shows an error, but
# the address it shows carries the code: pasting it into the page finishes the connection. It is
# the loopback address a "Desktop app" client is allowed to use, so the same client works here
# and with `familydb google auth` on a laptop.
CONSENT_RETURN = "http://127.0.0.1:53682/"
NOT_JSON = "That is not the file Google gave you: it should be JSON, starting with {."
WEB_CLIENT = (
    "That client is of type Web application. Create one of type Desktop app in Google Cloud "
    "(Credentials, Create credentials, OAuth client ID) and paste that one instead."
)
NO_CLIENT = (
    "That JSON has no OAuth client in it. Download it from the client's page in Google Cloud."
)
NO_CODE = "There is no code in that. Paste the whole address the browser was sent to."
MIXED_UP = "That address belongs to an earlier try. Start again and use the newest link."


class GoogleSetupError(ValueError):
    """Something the person connecting the calendar can put right; the message says what."""


def client_config(text: str) -> dict[str, Any]:
    """The OAuth client pasted into the page, checked for being the right kind."""
    try:
        config = json.loads(text)
    except ValueError:
        raise GoogleSetupError(NOT_JSON) from None
    if not isinstance(config, dict):
        raise GoogleSetupError(NOT_JSON)
    if "installed" not in config:
        raise GoogleSetupError(WEB_CLIENT if "web" in config else NO_CLIENT)
    return config


def begin_consent(config: dict[str, Any]) -> tuple[str, Any, str]:
    """Google's consent address, the flow that must finish it (it holds the PKCE secret), and
    the state the address will come back carrying."""
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(config, SCOPES, redirect_uri=CONSENT_RETURN)
    # offline and consent: a refresh token every time, so the calendar keeps working for months.
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    return url, flow, state


def finish_consent(flow: Any, pasted: str, token_path: Path, *, state: str | None = None) -> Any:
    """Exchange what was pasted (the address, or just the code) for a token, and save it."""
    pasted = pasted.strip()
    code = pasted
    if pasted.startswith(("http://", "https://")):
        query = parse_qs(urlsplit(pasted).query)
        if "error" in query:
            raise GoogleSetupError(f"Google said: {query['error'][0]}. Start again.")
        if state and query.get("state", [state])[0] != state:
            raise GoogleSetupError(MIXED_UP)
        code = (query.get("code") or [""])[0]
    if not code:
        raise GoogleSetupError(NO_CODE)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:  # oauthlib raises a family of its own; each means the same here
        raise GoogleSetupError(f"Google would not take that code ({exc}). Start again.") from exc
    creds = flow.credentials
    save_token(token_path, creds.to_json())
    return creds


def list_calendars(creds: Any) -> list[dict[str, Any]]:
    items = build_service(creds).calendarList().list().execute().get("items", [])
    return [
        {
            "id": item.get("id"),
            "summary": item.get("summary"),
            "primary": bool(item.get("primary", False)),
            "access": item.get("accessRole"),
        }
        for item in items
    ]


class GoogleCalendar:
    """CalendarAPI over the shared family calendar."""

    def __init__(self, settings: Settings) -> None:
        if not settings.google_calendar_id:
            raise ToolUnavailable("GOOGLE_CALENDAR_ID is not set")
        self.calendar_id = settings.google_calendar_id
        self.token_path = Path(settings.google_token_path)
        self.tz = settings.tzinfo
        self._service: Any = None
        # The underlying HTTP client is not thread-safe; the bot and the scheduler share this.
        self._lock = threading.Lock()

    def _events(self) -> Any:
        with self._lock:
            if self._service is None:
                self._service = build_service(load_credentials(self.token_path))
            return self._service.events()

    def _execute(self, request: Any, *, ignore: tuple[int, ...] = ()) -> Any:
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError

        try:
            with self._lock:
                return request.execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            if status in ignore:
                return None
            raise ToolError(f"Google Calendar error {status or '?'}: {exc.reason}") from exc
        except RefreshError as exc:
            raise ToolUnavailable(REAUTH) from exc

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            response = self._execute(
                self._events().list(
                    calendarId=self.calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=250,
                    pageToken=page_token,
                )
            )
            items.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return [parse_event(i, self.tz) for i in items if i.get("status") != "cancelled"]

    def get_event(self, event_id: str) -> CalendarEvent | None:
        item = self._execute(
            self._events().get(calendarId=self.calendar_id, eventId=event_id), ignore=(404, 410)
        )
        if not item or item.get("status") == "cancelled":
            return None
        return parse_event(item, self.tz)

    def insert_event(
        self,
        *,
        title: str,
        start: datetime | date,
        end: datetime | date,
        all_day: bool,
        location: str | None,
        description: str | None,
        event_id: str | None = None,
    ) -> CalendarEvent:
        body = event_body(
            tz=self.tz,
            title=title,
            start=start,
            end=end,
            all_day=all_day,
            location=location,
            description=description,
        )
        if event_id:
            body["id"] = event_id
        item = self._execute(
            self._events().insert(calendarId=self.calendar_id, body=body), ignore=(409,)
        )
        if item is None and event_id:
            existing = self.get_event(event_id)
            if existing is not None:
                return existing
            raise ToolError(
                "Calendar operation already exists but is unavailable; check Google Calendar"
            )
        return parse_event(item, self.tz)

    def patch_event(self, event_id: str, **changes: Any) -> CalendarEvent:
        body = event_body(tz=self.tz, clear_other_time_key=True, **changes)
        item = self._execute(
            self._events().patch(calendarId=self.calendar_id, eventId=event_id, body=body)
        )
        return parse_event(item, self.tz)

    def delete_event(self, event_id: str) -> None:
        """Delete an event. One already deleted by hand (404 or 410) counts as done."""
        self._execute(
            self._events().delete(calendarId=self.calendar_id, eventId=event_id),
            ignore=(404, 410),
        )
