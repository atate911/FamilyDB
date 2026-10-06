"""Google Calendar through the official client: one shared family calendar, reached by a service
account that the calendar was shared with. The family signs in to nothing and no token expires."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from familydb.config import Settings
from familydb.errors import ToolError, ToolUnavailable

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
KEY_REFUSED = (
    "Google no longer accepts the saved key; connect the calendar again on the settings page"
)
# How long the page may show what Google said rather than ask again (a few hundred ms per view).
# The bot's own writes forget what was read; an event added on a phone may take this long to show
# (the family's choice).
PAGE_READ_SECONDS = 60.0


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
    # Whether it takes the time up (Google's transparency: a "free" birthday does not).
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


@dataclass(frozen=True)
class CalendarChanges:
    """What changed since a sync token, and the next token. `events` maps an id to the event, or
    None when gone; with `full` the token was missing or too old, so `events` is the whole
    calendar and an id absent from it is gone too."""

    events: dict[str, CalendarEvent | None]
    token: str
    full: bool


class CalendarAPI(Protocol):
    """What the tools need from a calendar; tests fake it."""

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    def recent_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """What the page shows: `list_events`, or a recent enough answer."""
        ...

    def get_event(self, event_id: str) -> CalendarEvent | None: ...

    def changes(self, sync_token: str | None) -> CalendarChanges:
        """Everything changed since `sync_token` in one request; the whole calendar with no token
        or a stale one."""
        ...

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
    """The request body for insert or patch. Patches merge, so switching timed/all-day must null
    the key no longer used (`clear_other_time_key`)."""
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


def load_credentials(key_path: Path) -> Any:
    """Credentials from the saved service account key."""
    from google.oauth2 import service_account

    if not key_path.exists():
        raise ToolUnavailable(f"no Google key at {key_path}; connect the calendar on the page")
    try:
        info = json.loads(key_path.read_text(encoding="utf-8"))
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    except (ValueError, KeyError, AttributeError) as exc:
        raise ToolUnavailable(KEY_REFUSED) from exc


def save_key(key_path: Path, text: str) -> None:
    """Write the key owner-only, and whole: a half-written key is a lost calendar."""
    key_path.parent.mkdir(parents=True, exist_ok=True)
    fresh = key_path.with_name(key_path.name + ".new")
    handle = os.open(fresh, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    os.chmod(fresh, 0o600)  # in case an older file of that name had other rights
    os.replace(fresh, key_path)


# Connecting: the page tries the pasted key and calendar id before keeping either.
NOT_JSON = "That is not the file Google gave you: it should be JSON, starting with {."
NOT_A_KEY = (
    "That is not a service account key. In Google Cloud, open the service account, then Keys, "
    "Add key, Create new key, JSON, and paste everything in the file it saves."
)
NO_CALENDAR = (
    "Type the calendar's id: in Google Calendar, the calendar's settings, under Integrate calendar."
)
NOT_SHARED = (
    "Google cannot find that calendar for {email}. Check the id, and that the calendar is "
    "shared with {email}: in Google Calendar, the calendar's settings, Share with specific "
    "people."
)
API_OFF = (
    "Google Calendar is not turned on in the project that key belongs to. Turn on the Google "
    "Calendar API there, wait a minute, and try again."
)
READ_ONLY = (
    "{email} can see that calendar but not change it. In its sharing settings, give it "
    "'Make changes to events'."
)
CHECK_TITLE = "FamilyDB connection check"


class GoogleSetupError(ValueError):
    """Something the person connecting the calendar can put right; the message says what."""


def service_account_key(text: str) -> dict[str, Any]:
    """The pasted key file, checked for being a service account's."""
    from google.oauth2 import service_account

    try:
        info = json.loads(text)
    except ValueError:
        raise GoogleSetupError(NOT_JSON) from None
    if not isinstance(info, dict):
        raise GoogleSetupError(NOT_JSON)
    if info.get("type") != "service_account":
        raise GoogleSetupError(NOT_A_KEY)
    try:
        service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    except (ValueError, KeyError):
        raise GoogleSetupError(NOT_A_KEY) from None
    return info


def service_account_email(key_path: Path) -> str | None:
    """The saved key's address, which the calendar must be shared with."""
    try:
        return str(json.loads(key_path.read_text(encoding="utf-8"))["client_email"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def check_access(info: dict[str, Any], calendar_id: str) -> None:
    """Prove the key can read and change the calendar, leaving it as found: a read-only share looks
    the same until an event is made and deleted."""
    from google.auth.exceptions import RefreshError
    from google.oauth2 import service_account
    from googleapiclient.errors import HttpError

    calendar_id = calendar_id.strip()
    if not calendar_id:
        raise GoogleSetupError(NO_CALENDAR)
    email = info.get("client_email", "the service account")
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    events = build_service(creds).events()
    today = datetime.now(ZoneInfo("UTC")).date()
    body = {
        "summary": CHECK_TITLE,
        "start": {"date": today.isoformat()},
        "end": {"date": (today + timedelta(days=1)).isoformat()},
    }
    try:
        events.list(calendarId=calendar_id, maxResults=1).execute()
        made = events.insert(calendarId=calendar_id, body=body).execute()
        events.delete(calendarId=calendar_id, eventId=made["id"]).execute()
    except RefreshError:
        raise GoogleSetupError(
            "Google would not accept that key. It may have been deleted; make another."
        ) from None
    except HttpError as exc:
        raise GoogleSetupError(_explain(exc, email)) from exc


def _explain(exc: Any, email: str) -> str:

    status = getattr(exc.resp, "status", None)
    content = exc.content or b""
    if status == 403 and (b"accessNotConfigured" in content or b"SERVICE_DISABLED" in content):
        return API_OFF
    if status == 404:
        return NOT_SHARED.format(email=email)
    if status == 403:
        return READ_ONLY.format(email=email)
    return f"Google said {status or '?'}: {exc.reason}. Check the key and the calendar's id."


class GoogleCalendar:
    """CalendarAPI over the shared family calendar."""

    def __init__(self, settings: Settings) -> None:
        if not settings.google_calendar_id:
            raise ToolUnavailable("GOOGLE_CALENDAR_ID is not set")
        self.calendar_id = settings.google_calendar_id
        self.key_path = Path(settings.google_key_path)
        self.tz = settings.tzinfo
        self._service: Any = None
        # The HTTP client is not thread-safe; the bot and the scheduler share this.
        self._lock = threading.Lock()
        # What the page was last told per span of days, and when (PAGE_READ_SECONDS).
        self._read: dict[tuple[str, str], tuple[float, int, list[CalendarEvent]]] = {}
        self._read_lock = threading.Lock()
        self._writes = 0
        self._now = time.monotonic
        # Told when Google shuts the bot out (what it said) and when it answers again (None), for
        # an admin (alerts.py); set by App.
        self.report: Callable[[str | None], None] | None = None
        # Unknown at first, so the first answer clears a note from before a restart.
        self._troubled = True

    def _events(self) -> Any:
        with self._lock:
            if self._service is None:
                try:
                    self._service = build_service(load_credentials(self.key_path))
                except ToolUnavailable as exc:
                    self._shut_out(str(exc))
                    raise
            return self._service.events()

    def _shut_out(self, said: str) -> None:
        self._troubled = True
        if self.report is not None:
            self.report(said)

    def _execute(self, request: Any, *, ignore: tuple[int, ...] = ()) -> Any:
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError

        try:
            with self._lock:
                answer = request.execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            if status in ignore:
                return None
            raise ToolError(f"Google Calendar error {status or '?'}: {exc.reason}") from exc
        except RefreshError as exc:
            self._shut_out(KEY_REFUSED)
            raise ToolUnavailable(KEY_REFUSED) from exc
        if self._troubled:
            self._troubled = False
            if self.report is not None:
                self.report(None)
        return answer

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

    def recent_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """What Google said about these days within the last minute, unless written since; a
        failure is never kept."""
        key = (start.isoformat(), end.isoformat())
        with self._read_lock:
            kept = self._read.get(key)
            writes = self._writes
        if kept is not None and kept[1] == writes and self._now() - kept[0] < PAGE_READ_SECONDS:
            return list(kept[2])
        asked = self._now()
        events = self.list_events(start, end)
        with self._read_lock:
            # A write while Google was asked may postdate its answer: keep nothing.
            if self._writes == writes:
                self._read[key] = (asked, writes, events)
        return list(events)

    def changes(self, sync_token: str | None) -> CalendarChanges:
        events: dict[str, CalendarEvent | None] = {}
        page_token: str | None = None
        while True:
            response = self._execute(
                self._events().list(
                    calendarId=self.calendar_id,
                    syncToken=sync_token,
                    pageToken=page_token,
                    maxResults=2500,
                    fields="nextPageToken,nextSyncToken,items("
                    "id,status,summary,start,end,location,description,htmlLink,transparency)",
                ),
                ignore=(410,),  # token forgotten: start again from nothing
            )
            if response is None:
                if sync_token is None:
                    raise ToolError("Google Calendar error 410: no sync possible")
                return self.changes(None)
            for item in response.get("items", []):
                gone = item.get("status") == "cancelled"
                events[item["id"]] = None if gone else parse_event(item, self.tz)
            page_token = response.get("nextPageToken")
            if not page_token:
                return CalendarChanges(events, response["nextSyncToken"], full=sync_token is None)

    def _wrote(self) -> None:
        with self._read_lock:
            self._writes += 1
            self._read.clear()

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
        try:
            item = self._execute(
                self._events().insert(calendarId=self.calendar_id, body=body), ignore=(409,)
            )
        finally:
            self._wrote()
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
        try:
            item = self._execute(
                self._events().patch(calendarId=self.calendar_id, eventId=event_id, body=body)
            )
        finally:
            self._wrote()
        return parse_event(item, self.tz)

    def delete_event(self, event_id: str) -> None:
        """Delete an event; one already deleted by hand (404/410) counts as done."""
        try:
            self._execute(
                self._events().delete(calendarId=self.calendar_id, eventId=event_id),
                ignore=(404, 410),
            )
        finally:
            self._wrote()
