"""Card guessing mode."""

from __future__ import annotations

import random

from game_common import fetch_entities, find_entity, run_guessing_round

RARITY_RANKS = {
    "basic": 0,
    "starter": 0,
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "ancient": 4,
}
CARD_TYPES = {"Attack", "Skill", "Power"}


def fetch_cards(color: str | None = None) -> list[dict]:
    params = {"color": color} if color else None
    return fetch_entities(
        "/api/cards",
        params,
        lambda card: card.get("type") in CARD_TYPES,
    )


def find_card(cards: list[dict], query: str) -> dict | None:
    return find_entity(cards, query)


def cost_clue(
    guess: dict,
    answer: dict,
    field: str,
    x_field: str | None = None,
    default_value: int | float | None = None,
) -> str:
    guess_is_x = bool(guess.get(x_field)) if x_field else False
    answer_is_x = bool(answer.get(x_field)) if x_field else False
    if guess_is_x or answer_is_x:
        return "MATCH" if guess_is_x and answer_is_x else "NO CLUE"

    guess_cost = guess.get(field)
    answer_cost = answer.get(field)
    if guess_cost is None and default_value is not None:
        guess_cost = default_value
    if answer_cost is None and default_value is not None:
        answer_cost = default_value
    if not isinstance(guess_cost, (int, float)) or not isinstance(answer_cost, (int, float)):
        return "NO CLUE"
    if guess_cost == answer_cost:
        return "MATCH"
    return "UP" if guess_cost < answer_cost else "DOWN"


def rarity_clue(guess: dict, answer: dict) -> str:
    guess_rarity = str(guess.get("rarity", "")).casefold()
    answer_rarity = str(answer.get("rarity", "")).casefold()
    if guess_rarity == answer_rarity:
        return "MATCH"

    guess_rank = RARITY_RANKS.get(guess_rarity)
    answer_rank = RARITY_RANKS.get(answer_rarity)
    if guess_rank is None or answer_rank is None:
        return "MATCH" if guess_rank == answer_rank == 0 else "NO CLUE"
    if guess_rank == answer_rank:
        return "MATCH"
    return "UP" if guess_rank < answer_rank else "DOWN"


def clue_results(guess: dict, answer: dict) -> dict[str, str]:
    return {
        "Color": "MATCH" if guess.get("color") == answer.get("color") else "MISS",
        "Type": "MATCH" if guess.get("type") == answer.get("type") else "MISS",
        "Rarity": rarity_clue(guess, answer),
        "Cost": cost_clue(guess, answer, "cost", "is_x_cost"),
        "Stars": cost_clue(guess, answer, "star_cost", "is_x_star_cost", default_value=0),
    }


def print_clues(
    guess: dict,
    answer: dict,
    locked_values: dict[str, object] | None = None,
) -> None:
    results = clue_results(guess, answer)
    values = {
        "Color": str(guess.get("color", "?")).upper(),
        "Type": str(guess.get("type", "?")).upper(),
        "Rarity": str(guess.get("rarity", "?")).upper(),
        "Cost": "X" if guess.get("is_x_cost") else guess.get("cost", "?"),
        "Stars": "X" if guess.get("is_x_star_cost") else guess.get("star_cost"),
    }
    has_star_cost = bool(guess.get("is_x_star_cost")) or (
        isinstance(values["Stars"], (int, float)) and values["Stars"] > 0
    )
    if locked_values is None:
        locked_values = {}
    for field, result in results.items():
        if result == "MATCH" and (field != "Stars" or has_star_cost):
            locked_values[field] = values[field]

    details = [
        f"colour {locked_values.get('Color', results['Color'])} | "
        f"type {locked_values.get('Type', results['Type'])} | "
        f"rarity {locked_values.get('Rarity', results['Rarity'])} | "
        f"COST {locked_values.get('Cost', results['Cost'])}"
    ]
    if has_star_cost or "Stars" in locked_values:
        details.append(f"STARS {locked_values.get('Stars', results['Stars'])}")
    print("  " + " | ".join(details))


def run(color: str | None = None, seed: int | None = None) -> bool:
    cards = fetch_cards(color)
    print(f"Spiredle | Cards | {len(cards)} cards loaded from Spire Codex")
    if color:
        print(f"Colour filter: {color}")
    return run_guessing_round(
        cards,
        mode_name="card",
        rng=random.Random(seed),
        after_guess=print_clues,
    )