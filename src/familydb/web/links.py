"""Every page outside FamilyDB the page links to; `familydb doctor --online` checks each."""

from __future__ import annotations

LINKS: dict[str, str] = {
    "openai_signup": "https://platform.openai.com/signup",
    "openai_billing": "https://platform.openai.com/settings/organization/billing/overview",
    "openai_limits": "https://platform.openai.com/settings/organization/limits",
    "openai_keys": "https://platform.openai.com/api-keys",
    "anthropic_console": "https://console.anthropic.com/",
    "anthropic_billing": "https://console.anthropic.com/settings/billing",
    "anthropic_limits": "https://console.anthropic.com/settings/limits",
    "anthropic_keys": "https://console.anthropic.com/settings/keys",
    "gemini_keys": "https://aistudio.google.com/apikey",
    "google_cloud": "https://console.cloud.google.com/",
    "google_project": "https://console.cloud.google.com/projectcreate",
    "google_calendar_api": (
        "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com"
    ),
    "google_service_accounts": "https://console.cloud.google.com/iam-admin/serviceaccounts",
    "google_calendar_settings": "https://calendar.google.com/calendar/r/settings",
    "telegram": "https://telegram.org/",
    "botfather": "https://t.me/BotFather",
    "ticketmaster_developer": "https://developer.ticketmaster.com/",
}
