"""Talks to animeheaven.me: search, episode list, download link of an episode."""
import re

import requests
from bs4 import BeautifulSoup

BASE = "https://animeheaven.me/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) anime-dl"}
TIMEOUT = 20

session = requests.Session()
session.headers.update(HEADERS)


class SiteError(Exception):
    """The site answered, but not with what we expected."""


def _soup(path: str, params: dict | None = None, cookies: dict | None = None) -> BeautifulSoup:
    resp = session.get(BASE + path, params=params, cookies=cookies, timeout=TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def search(query: str) -> list[dict]:
    """Return the shows matching `query`, as [{"title", "id"}], without duplicates."""
    soup = _soup("search.php", {"s": query})
    results, seen = [], set()
    for a in soup.select("div.similarname a[href^='anime.php?']"):
        show_id = a["href"].split("?", 1)[1]
        if show_id not in seen:
            seen.add(show_id)
            results.append({"title": a.get_text(strip=True), "id": show_id})
    return results


def episodes(show_id: str) -> tuple[str, list[dict]]:
    """Return (show title, episodes oldest first as [{"number", "released", "key"}])."""
    soup = _soup("anime.php?" + show_id)
    title_el = soup.select_one(".infotitle")
    title = title_el.get_text(strip=True) if title_el else show_id
    eps = []
    for a in soup.select("a[onclick^='gatea']"):
        num = a.select_one(".watch2")
        match = re.search(r"[0-9a-f]{32}", a.get("onclick", ""))
        if not num or not match:
            continue
        info = a.select(".watch1")  # [0] = "Episode" label, [1] = "N d ago"
        eps.append({
            "number": num.get_text(strip=True),
            "released": info[1].get_text(strip=True) if len(info) > 1 else "",
            "key": match.group(0),
        })
    eps.reverse()  # the page lists newest first
    return title, eps


def resolve_download(key: str) -> str:
    """Open the episode's gate page (which activates the link) and return its download URL."""
    soup = _soup("gate.php", cookies={"key": key})
    pattern = re.compile(r"^https://[a-z0-9]+\.animeheaven\.me/video\.mp4\?" + key + r"&d$")
    for a in soup.find_all("a", href=True):
        if pattern.match(a["href"]):
            return a["href"]
    raise SiteError(f"no download link on the gate page for key {key}")
