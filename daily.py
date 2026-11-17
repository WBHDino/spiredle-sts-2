"""Deterministic daily puzzles and local streak tracking."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import art
import card_text
import cards
import encounters
import enemies
import intent_order
import potions
import relics

DAILY_MODES = {
    "cards": cards.run,
    "enemies": enemies.run,
    "relics": relics.run,
    "potions": potions.run,
    "card-text": card_text.run,
    "encounters": encounters.run,
    "intent-order": intent_order.run,
    "art": art.run,
}
DEFAULT_STATS_PATH = Path.home() / ".spiredle" / "daily_stats.json"


def daily_seed(day: str, mode: str) -> int:
    digest = hashlib.sha256(f"spiredle:{day}:{mode}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def load_daily_stats(path: Path = DEFAULT_STATS_PATH) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"modes": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("modes"), dict):
        return {"modes": {}}
    return payload


def record_daily_result(
    path: Path,
    mode: str,
    day: str,
    won: bool,
) -> tuple[dict, bool]:
    stats = load_daily_stats(path)
    modes = stats["modes"]
    previous = modes.get(mode, {})
    if previous.get("last_played") == day:
        return previous, False

    try:
        yesterday = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    except ValueError:
        raise ValueError("Daily date must use YYYY-MM-DD format.") from None

    if won:
        current_streak = previous.get("current_streak", 0) + 1 if (
            previous.get("last_played") == yesterday and previous.get("last_result") is True
        ) else 1
    else:
        current_streak = 0
    result = {
        "last_played": day,
        "last_result": won,
        "current_streak": current_streak,
        "best_streak": max(previous.get("best_streak", 0), current_streak),
    }
    modes[mode] = result

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)
    return result, True


def run(
    mode: str = "cards",
    *,
    stats_path: Path = DEFAULT_STATS_PATH,
    day: str | None = None,
    runners: dict[str, Callable[..., bool]] | None = None,
) -> bool:
    mode = mode.casefold()
    selected_runners = runners or DAILY_MODES
    if mode not in selected_runners:
        raise ValueError(f"Unknown daily mode: {mode}")

    day = day or datetime.now(timezone.utc).date().isoformat()
    seed = daily_seed(day, mode)
    previous = load_daily_stats(stats_path)["modes"].get(mode, {})
    print(f"Daily Spiredle | {mode} | {day} | Seed {seed}")
    print(f"Current streak: {previous.get('current_streak', 0)} | Best streak: {previous.get('best_streak', 0)}")
    won = selected_runners[mode](seed=seed)

    try:
        result, recorded = record_daily_result(stats_path, mode, day, won)
    except OSError as error:
        print(f"Could not save daily stats: {error}")
        return won
    if recorded:
        print(f"Daily streak: {result['current_streak']} | Best streak: {result['best_streak']}")
    else:
        print("Today's result was already recorded; the streak was not changed.")
    return won