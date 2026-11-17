"""Guess the listed order of a monster's attack-pattern moves."""

from __future__ import annotations

import random

from game_common import fetch_entities, normalize

GUESS_LIMIT = 6


def get_intent_sequence(monster: dict) -> list[dict]:
    moves = monster.get("moves")
    pattern = monster.get("attack_pattern")
    states = pattern.get("states") if isinstance(pattern, dict) else None
    if not isinstance(moves, list) or not isinstance(states, list):
        return []

    moves_by_id = {
        str(move.get("id")): move
        for move in moves
        if isinstance(move, dict) and move.get("id") and move.get("name")
    }
    sequence = [
        moves_by_id[str(state["move_id"])]
        for state in states
        if isinstance(state, dict)
        and state.get("type") == "move"
        and state.get("move_id")
        and str(state["move_id"]) in moves_by_id
    ]
    return sequence if len(sequence) >= 2 else []


def fetch_order_enemies() -> list[dict]:
    return fetch_entities("/api/monsters", predicate=lambda monster: len(get_intent_sequence(monster)) >= 2)


def resolve_move_order(query: str, options: list[dict]) -> list[dict] | None:
    parts = [part.strip() for part in query.split(",")]
    if len(parts) != len(options) or any(not part for part in parts):
        return None

    by_id = {normalize(str(move["id"])): move for move in options}
    by_name: dict[str, list[dict]] = {}
    for move in options:
        by_name.setdefault(normalize(str(move["name"])), []).append(move)

    resolved: list[dict] = []
    for part in parts:
        key = normalize(part)
        move = by_id.get(key)
        if move is None:
            matches = by_name.get(key, [])
            if len(matches) != 1:
                return None
            move = matches[0]
        resolved.append(move)
    if len({str(move["id"]) for move in resolved}) != len(options):
        return None
    return resolved


def correct_positions(guess: list[dict], answer: list[dict]) -> int:
    return sum(
        str(guess_move["id"]) == str(answer_move["id"])
        for guess_move, answer_move in zip(guess, answer)
    )


def _show_options(options: list[dict]) -> None:
    print("Moves to order:")
    for index, move in enumerate(options, start=1):
        print(f"  {index}. {move['name']} [{move['id']}]")
    print("Enter every move ID or unambiguous name, separated by commas.")


def run(seed: int | None = None) -> bool:
    monsters = fetch_order_enemies()
    rng = random.Random(seed)
    answer = rng.choice(monsters)
    sequence = get_intent_sequence(answer)
    options_by_id = {str(move["id"]): move for move in sequence}
    options = list(options_by_id.values())
    rng.shuffle(options)

    print(f"Spiredle | Intent Order | {len(monsters)} monsters with an ordered pattern loaded")
    _show_options(options)
    attempted: set[tuple[str, ...]] = set()
    for attempt in range(1, GUESS_LIMIT + 1):
        try:
            query = input(f"Order {attempt}/{GUESS_LIMIT}: ").strip()
        except EOFError:
            print("\nRound ended.")
            return False
        if not query:
            continue
        if normalize(query) in {"quit", "exit"}:
            correct_order = ", ".join(str(move["name"]) for move in sequence)
            print(f"The monster was {answer['name']}. Pattern order: {correct_order}.")
            return False
        if query == "?":
            _show_options(options)
            continue

        guess = resolve_move_order(query, options)
        if guess is None:
            print("Enter each listed move exactly once, separated by commas; use IDs for duplicate names.")
            continue
        signature = tuple(str(move["id"]) for move in guess)
        if signature in attempted:
            print("You already tried that order; it does not use a turn.")
            continue
        attempted.add(signature)

        positions = correct_positions(guess, sequence)
        if positions == len(sequence):
            print(f"Correct! {answer['name']} in {attempt} guess(es).")
            return True
        print(f"{positions}/{len(sequence)} moves are in the correct position.")

    correct_order = ", ".join(str(move["name"]) for move in sequence)
    print(f"Out of guesses. The monster was {answer['name']}. Pattern order: {correct_order}.")
    return False