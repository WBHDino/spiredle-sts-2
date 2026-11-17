"""Artwork-only card guessing mode."""

from __future__ import annotations

import random
from urllib.parse import urljoin

from cards import CARD_TYPES, find_card
from game_common import API_URL, fetch_entities, run_guessing_round


def fetch_art_cards(color: str | None = None) -> list[dict]:
    params = {"color": color} if color else None
    return fetch_entities(
        "/api/cards",
        params,
        lambda card: card.get("type") in CARD_TYPES and bool(card.get("image_url")),
    )


def artwork_url(card: dict) -> str:
    return urljoin(API_URL, str(card.get("image_url") or ""))


def show_artwork(card: dict) -> None:
    print(f"Artwork clue: {artwork_url(card)}")


def run(color: str | None = None, seed: int | None = None) -> bool:
    cards = fetch_art_cards(color)
    print(f"Spiredle | Art Guess | {len(cards)} cards with artwork loaded from Spire Codex")
    if color:
        print(f"Colour filter: {color}")
    print("Open the artwork link in a browser; the full card image is not used.")
    return run_guessing_round(
        cards,
        mode_name="card",
        rng=random.Random(seed),
        round_clues=show_artwork,
        guess_resolver=find_card,
        answer_checker=lambda guess, answer: str(guess["id"]) == str(answer["id"]),
    )