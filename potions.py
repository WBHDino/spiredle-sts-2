"""Potion guessing mode."""

from __future__ import annotations

import random

from game_common import fetch_entities, run_guessing_round
from item_common import print_item_clues


def fetch_potions(pool: str | None = None) -> list[dict]:
    params = {"pool": pool} if pool else None
    return fetch_entities("/api/potions", params)


def run(pool: str | None = None, seed: int | None = None) -> bool:
    potions = fetch_potions(pool)
    print(f"Spiredle | Potions | {len(potions)} potions loaded from Spire Codex")
    if pool:
        print(f"Pool filter: {pool}")
    return run_guessing_round(
        potions,
        mode_name="potion",
        rng=random.Random(seed),
        after_guess=print_item_clues,
    )