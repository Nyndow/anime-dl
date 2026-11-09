"""Interactive flow: search -> show -> episodes -> downloader -> download."""
import logging
import os

import questionary
import requests

import downloader
import settings
import site_api

LOG_PATH = os.path.expanduser(
    os.getenv("ANIME_DL_LOG_PATH",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "anime-dl.log"))
)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
)
logger = logging.getLogger(__name__)

BACK = "__back__"
ALL = "__all__"


def pause(message: str) -> None:
    print(message)
    input("Press Enter...")


def choose_show() -> dict | None:
    """Ask for a query and return the chosen show, or None to go back to the main menu."""
    query = questionary.text("Search for a show:").ask()
    if not query or not query.strip():
        return None
    try:
        results = site_api.search(query.strip())
    except requests.RequestException:
        logger.exception("search failed for %r", query)
        pause(f"Search failed. Details in {LOG_PATH}")
        return None
    if not results:
        pause(f"No results for {query!r}.")
        return None

    choices = [questionary.Choice(r["title"], value=r) for r in results]
    choices.append(questionary.Choice("◂ Back", value=BACK))
    picked = questionary.select(f"{len(results)} result(s):", choices=choices).ask()
    return None if picked in (None, BACK) else picked


def choose_episodes(show: dict) -> tuple[str, list[dict]]:
    """Return (show title, chosen episodes); an empty list means nothing to download."""
    try:
        title, eps = site_api.episodes(show["id"])
    except requests.RequestException:
        logger.exception("episode list failed for %s", show["id"])
        pause(f"Could not load the episodes. Details in {LOG_PATH}")
        return show["title"], []
    if not eps:
        pause("No episodes found.")
        return title, []

    choices = [questionary.Choice(f"Select all ({len(eps)})", value=ALL)]
    choices += [questionary.Choice(f"Episode {e['number']:>4}   {e['released']}", value=e) for e in eps]
    picked = questionary.checkbox(f"{title} — SPACE to select, ENTER to confirm:", choices=choices).ask()
    if not picked:
        return title, []
    return title, eps if ALL in picked else picked


def choose_tool() -> str | None:
    """The downloader from the settings, or ask among the installed ones."""
    tools = downloader.available_tools()
    if not tools:
        pause("Neither aria2c nor wget is installed. Install one of them first.")
        return None
    preferred = settings.load()["downloader"]
    if preferred in tools:
        return preferred
    if len(tools) == 1:
        return tools[0]
    return questionary.select("Downloader:", choices=[
        questionary.Choice("aria2 (fast, several connections)", value="aria2"),
        questionary.Choice("wget (simple)", value="wget"),
    ]).ask()


def episode_filename(title: str, number: str) -> str:
    """'Durarara!! - E01.mp4'; non-numeric numbers (e.g. '12.5', 'OVA') are kept as they are."""
    label = f"E{int(number):02d}" if number.isdigit() else f"E{number}"
    return f"{title} - {label}.mp4"


def download_episodes(title: str, eps: list[dict], tool: str) -> None:
    """Resolve each episode's link right before downloading it, then report the result."""
    insecure = settings.load()["no_certificate_check"]
    failed = []
    for i, ep in enumerate(eps, 1):
        name = episode_filename(title, ep["number"])
        print(f"\n[{i}/{len(eps)}] {name}")
        try:
            url = site_api.resolve_download(ep["key"])
        except (requests.RequestException, site_api.SiteError):
            logger.exception("could not resolve episode %s of %s", ep["number"], title)
            print("  could not get the download link, skipped")
            failed.append(ep["number"])
            continue
        if not downloader.download(tool, url, title, name, insecure):
            failed.append(ep["number"])

    where = downloader.target_dir(title)
    done = len(eps) - len(failed)
    print(f"\n{done}/{len(eps)} episode(s) downloaded to {where}")
    if failed:
        print(f"Failed: episode(s) {', '.join(failed)}. Run again to resume them; details in {LOG_PATH}")


def run() -> None:
    """Main menu loop. Ctrl+C at any prompt returns to the menu or exits."""
    while True:
        action = questionary.select("anime-dl", choices=[
            questionary.Choice("Search", value="search"),
            questionary.Choice("Settings", value="settings"),
            questionary.Choice("Exit", value="exit"),
        ]).ask()

        if action in (None, "exit"):
            return
        if action == "settings":
            settings.menu()
            continue

        show = choose_show()
        if not show:
            continue
        title, eps = choose_episodes(show)
        if not eps:
            continue
        tool = choose_tool()
        if not tool:
            continue
        try:
            download_episodes(title, eps, tool)
        except KeyboardInterrupt:
            print("\nStopped. Partial files are kept; run again to resume.")
        pause("")
