#!/usr/bin/env python3
"""Search animeheaven.me and list the episodes of a result (requests + BeautifulSoup)."""
import argparse
import sys

import requests
from bs4 import BeautifulSoup

BASE = "https://animeheaven.me/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) animeheaven-scraper"}

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(path: str, params: dict | None = None) -> BeautifulSoup:
    resp = session.get(BASE + path, params=params, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def search(query: str) -> list[tuple[str, str]]:
    soup = get_soup("search.php", {"s": query})
    results, seen = [], set()
    for a in soup.select("div.similarname a[href^='anime.php?']"):
        anime_id = a["href"].split("?", 1)[1]
        if anime_id not in seen:
            seen.add(anime_id)
            results.append((a.get_text(strip=True), anime_id))
    return results


def episodes(anime_id: str) -> tuple[str, list[dict]]:
    soup = get_soup("anime.php?" + anime_id)
    title_el = soup.select_one(".infotitle")
    title = title_el.get_text(strip=True) if title_el else anime_id
    eps = []
    for a in soup.select("a[onclick^='gatea']"):
        num = a.select_one(".watch2")
        info = a.select(".watch1")  # [0] = "Episode" label, [1] = "N d ago"
        if not num:
            continue
        eps.append({
            "episode": num.get_text(strip=True),
            "released": info[1].get_text(strip=True) if len(info) > 1 else "",
            "key": a.get("id", ""),
        })
    eps.reverse()  # page lists newest first
    return title, eps


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", help="search text, e.g. 'naruto'")
    ap.add_argument("-n", "--pick", type=int, default=1, help="result number to open (1-based, default 1)")
    args = ap.parse_args()

    try:
        results = search(args.query)
    except requests.RequestException as e:
        sys.exit(f"Search failed: {e}")
    if not results:
        sys.exit(f"No results for {args.query!r}")
    print(f"Search results for {args.query!r}:")
    for i, (title, aid) in enumerate(results, 1):
        print(f"  {i:2}. {title}  [anime.php?{aid}]")

    if not 1 <= args.pick <= len(results):
        sys.exit(f"--pick must be between 1 and {len(results)}")
    try:
        title, eps = episodes(results[args.pick - 1][1])
    except requests.RequestException as e:
        sys.exit(f"Fetching episodes failed: {e}")
    print(f"\n{title}: {len(eps)} episodes")
    for e in eps:
        print(f"  Episode {e['episode']:>5}  ({e['released']})")


if __name__ == "__main__":
    main()
