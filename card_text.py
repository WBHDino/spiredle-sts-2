"""Card guessing mode with progressively revealed card text."""

from __future__ import annotations

import random
import re

from cards import CARD_TYPES, find_card
from game_common import fetch_entities, run_guessing_round

GUESS_LIMIT = 6


def fetch_text_cards(color: str | None = None) -> list[dict]:
    params = {"color": color} if color else None
    return fetch_entities(
        "/api/cards",
        params,
        lambda card: card.get("type") in CARD_TYPES and bool(card.get("description")),
    )


def staged_description(description: str, attempt: int, total: int = GUESS_LIMIT) -> str:
    clean_text = re.sub(r"\[(?!star(?::[^]]*)?\])[^]]+\]", " ", description, flags=re.IGNORECASE)
    clean_text = re.sub(r"\[star(?::[^]]*)?\]", "[energy/star]", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"\s+([.,!?;:])", r"\1", clean_text)
    words = clean_text.split()
    if not words:
        return "No card text is available."
    revealed_count = min(len(words), (len(words) * attempt + total - 1) // total)
    return " ".join(words[:revealed_count])


def _make_text_revealer():
    def reveal(answer: dict, attempt: int) -> None:
        snippet = staged_description(str(answer.get("description") or ""), attempt)
        print(f"Card text ({attempt}/{GUESS_LIMIT}): {snippet}")

    return reveal


def run(color: str | None = None, seed: int | None = None) -> bool:
    cards = fetch_text_cards(color)
    print(f"Spiredle | Card Text | {len(cards)} playable cards loaded from Spire Codex")
    if color:
        print(f"Colour filter: {color}")
    return run_guessing_round(
        cards,
        mode_name="card",
        rng=random.Random(seed),
        before_guess=_make_text_revealer(),
        guess_resolver=find_card,
        answer_checker=lambda guess, answer: str(guess["id"]) == str(answer["id"]),
        guess_limit=lambda _answer: GUESS_LIMIT,
    )