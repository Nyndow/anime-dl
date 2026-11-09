"""User settings stored in a JSON file, and their menu."""
import json
import logging
import os

import questionary

SETTINGS_PATH = os.path.expanduser(
    os.getenv("ANIME_DL_SETTINGS_PATH",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "settings.json"))
)

DEFAULTS = {
    "no_certificate_check": False,  # True = skip TLS verification in aria2/wget
    "downloader": "ask",            # "ask", "aria2" or "wget"
}

logger = logging.getLogger(__name__)


def load() -> dict:
    """Return the saved settings merged over the defaults (missing keys get their default)."""
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            saved = json.load(f)
    except FileNotFoundError:
        saved = {}
    except (OSError, json.JSONDecodeError):
        logger.exception("unreadable settings file %s, using defaults", SETTINGS_PATH)
        saved = {}
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def save(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


def menu() -> None:
    """Settings menu: certificate check and default downloader. Returns on Back or Ctrl+C."""
    while True:
        s = load()
        cert = "DISABLED (unsafe)" if s["no_certificate_check"] else "enabled"
        choice = questionary.select(
            "Settings:",
            choices=[
                questionary.Choice(f"Certificate check: {cert}", value="cert"),
                questionary.Choice(f"Default downloader: {s['downloader']}", value="downloader"),
                questionary.Choice("Back", value="back"),
            ],
        ).ask()

        if choice == "cert":
            s["no_certificate_check"] = not s["no_certificate_check"]
            save(s)
        elif choice == "downloader":
            picked = questionary.select("Default downloader:", choices=["ask", "aria2", "wget"],
                                        default=s["downloader"]).ask()
            if picked:
                s["downloader"] = picked
                save(s)
        else:
            return
