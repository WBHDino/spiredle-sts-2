"""Shared clue formatting for relic and potion modes."""

from __future__ import annotations

import re

from game_common import normalize

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "all", "by", "for", "from",
    "in", "into", "of", "on", "or", "the", "to", "upon", "your",
}


def effect_terms(entity: dict) -> set[str]:
    description = re.sub(r"\[[^]]+\]", " ", str(entity.get("description") or ""))
    words = re.findall(r"[a-z]+", description.casefold())
    return {word for word in words if len(word) > 2 and word not in STOP_WORDS}


def item_clue_results(guess: dict, answer: dict) -> dict[str, object]:
    shared_terms = sorted(effect_terms(guess) & effect_terms(answer))
    return {
        "Rarity": normalize(str(guess.get("rarity", ""))) == normalize(str(answer.get("rarity", ""))),
        "Pool": normalize(str(guess.get("pool", ""))) == normalize(str(answer.get("pool", ""))),
        "Effect": shared_terms,
    }


def print_item_clues(
    guess: dict,
    answer: dict,
    locked_values: dict[str, object],
) -> None:
    results = item_clue_results(guess, answer)
    for field in ("Rarity", "Pool"):
        if results[field]:
            locked_values.setdefault(field, str(guess.get(field.casefold(), "?")).upper())

    rarity = locked_values.get("Rarity", "MATCH" if results["Rarity"] else "MISS")
    pool = locked_values.get("Pool", "MATCH" if results["Pool"] else "MISS")
    shared_terms = results["Effect"]
    effect_hint = ", ".join(shared_terms) if shared_terms else "no shared terms"
    print(f"  RARITY {rarity} | POOL {pool} | SHARED EFFECT TERMS {effect_hint}")