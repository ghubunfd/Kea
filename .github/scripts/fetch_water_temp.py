#!/usr/bin/env python3
"""Fetch current Neusiedler See water temperature and update water.json."""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

URL = "https://www.wassertemperatur.org/neusiedler-see/"
UA = "Mozilla/5.0 (compatible; KeaWetterBot/1.0; +https://github.com/ghubunfd/Kea)"
MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def fetch_html() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_temp(html: str) -> float:
    anchor = "Aktuelle Wassertemperatur im Neusiedler See"
    i = html.find(anchor)
    if i < 0:
        raise SystemExit("anchor phrase not found on page")
    snippet = html[i : i + 800]
    m = re.search(r"(\d{1,2})(?:[.,](\d))?\s*°\s*C", snippet)
    if not m:
        raise SystemExit(f"no temperature value found near anchor: {snippet[:200]!r}")
    whole = m.group(1)
    dec = m.group(2) or "0"
    return float(f"{whole}.{dec}")


def german_date(dt: datetime) -> str:
    return f"{dt.day}. {MONTHS_DE[dt.month - 1]} {dt.year}"


def main() -> None:
    html = fetch_html()
    temp = parse_temp(html)

    now = datetime.now(timezone.utc)
    iso = now.strftime("%Y-%m-%d")

    try:
        with open("water.json", encoding="utf-8") as f:
            prev = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        prev = {}

    history = prev.get("history") or []
    if not isinstance(history, list):
        history = []

    if history and history[-1].get("date") == iso:
        history[-1]["tempC"] = temp
    else:
        history.append({"date": iso, "tempC": temp})
    history = history[-14:]

    if len(history) >= 8:
        trend = round(temp - history[-8]["tempC"], 1)
    elif len(history) >= 2:
        trend = round(temp - history[0]["tempC"], 1)
    else:
        trend = 0.0

    payload = {
        "tempC": temp,
        "stampIso": iso,
        "stampDe": german_date(now),
        "trend7d": trend,
        "history": history,
        "source": URL,
    }

    with open("water.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"water temp = {temp} °C ({iso}), trend7d = {trend:+.1f}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
