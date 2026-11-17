"""Enemy guessing mode using the Spire Codex monster move catalogue."""

from __future__ import annotations

import random
from collections.abc import Callable

from game_common import fetch_entities, find_entity, normalize, run_guessing_round

DECIMILLIPEDE_SEGMENT_IDS = {
    "DECIMILLIPEDE_SEGMENT_BACK",
    "DECIMILLIPEDE_SEGMENT_FRONT",
    "DECIMILLIPEDE_SEGMENT_MIDDLE",
}
DECIMILLIPEDE_ALIAS = {"id": "DECIMILLIPEDE_FAMILY", "name": "Decimillipede"}


def _has_intent_clues(enemy: dict) -> bool:
    moves = enemy.get("moves")
    return isinstance(moves, list) and any(
        isinstance(move, dict)
        and move.get("name")
        and str(move.get("name")).casefold() != "nothing"
        and move.get("intent")
        and str(move.get("intent")).casefold() != "unknown"
        for move in moves
    )


def fetch_enemies(enemy_type: str | None = None) -> list[dict]:
    params = {"type": enemy_type} if enemy_type else None
    return fetch_entities("/api/monsters", params, _has_intent_clues)


def _is_decimillipede_segment(enemy: dict) -> bool:
    return str(enemy.get("id", "")).upper() in DECIMILLIPEDE_SEGMENT_IDS


def get_enemy_intents(enemy: dict) -> list[dict]:
    moves = enemy.get("moves")
    if not isinstance(moves, list):
        return []
    return [
        move
        for move in moves
        if isinstance(move, dict)
        and move.get("name")
        and str(move.get("name")).casefold() != "nothing"
        and move.get("intent")
        and str(move.get("intent")).casefold() != "unknown"
    ]


def find_enemy(enemies: list[dict], query: str) -> dict | None:
    if normalize(query) == "decimillipede" and any(
        _is_decimillipede_segment(enemy) for enemy in enemies
    ):
        return DECIMILLIPEDE_ALIAS
    return find_entity(enemies, query)


def is_correct_enemy(guess: dict, answer: dict) -> bool:
    if guess.get("id") == DECIMILLIPEDE_ALIAS["id"]:
        return _is_decimillipede_segment(answer)
    return str(guess.get("id")) == str(answer.get("id"))


def _format_damage(damage: dict, hit_count: int | None) -> str:
    normal = damage.get("normal")
    ascension = damage.get("ascension")
    if normal is None:
        return ""
    amount = f"{normal}"
    if isinstance(ascension, (int, float)) and ascension != normal:
        amount += f" (Asc. {ascension})"
    amount += " damage"
    if isinstance(hit_count, int) and hit_count > 1:
        amount += f" x {hit_count}"
    return amount


def format_intent(move: dict) -> str:
    """Format the known effects attached to one monster move."""
    effects: list[str] = []
    damage = move.get("damage")
    if isinstance(damage, dict):
        formatted_damage = _format_damage(damage, damage.get("hit_count"))
        if formatted_damage:
            effects.append(formatted_damage)

    block = move.get("block")
    if isinstance(block, (int, float)) and block:
        effects.append(f"{block} block")
    heal = move.get("heal")
    if isinstance(heal, (int, float)) and heal:
        effects.append(f"{heal} heal")

    powers = move.get("powers")
    if isinstance(powers, list):
        for power in powers:
            if not isinstance(power, dict) or not power.get("power_id"):
                continue
            power_name = str(power["power_id"]).replace("_", " ").title()
            amount = power.get("amount")
            target = power.get("target")
            effect = f"{power_name} {amount}" if amount is not None else power_name
            if target:
                effect += f" ({target})"
            effects.append(effect)

    intent_name = str(move.get("intent") or "Unknown")
    move_name = str(move.get("name") or "Unnamed move")
    effect_text = ", ".join(effects) if effects else "no numeric effect listed"
    return f"{move_name} | {intent_name}: {effect_text}"


def make_intent_revealer(rng: random.Random) -> Callable[[dict, int], None]:
    remaining_moves: list[dict] | None = None

    def reveal(answer: dict, _attempt: int) -> None:
        nonlocal remaining_moves
        if remaining_moves is None:
            remaining_moves = get_enemy_intents(answer)
        move = rng.choice(remaining_moves)
        remaining_moves.remove(move)
        print(f"Intent clue: {format_intent(move)}")

    return reveal


def run(enemy_type: str | None = None, seed: int | None = None) -> bool:
    enemies = fetch_enemies(enemy_type)
    rng = random.Random(seed)
    print(f"Spiredle | Enemies | {len(enemies)} enemies loaded from Spire Codex")
    if enemy_type:
        print(f"Enemy type filter: {enemy_type}")
    print("One random intent is revealed before each guess; invalid and repeated entries do not advance it.")
    return run_guessing_round(
        enemies,
        mode_name="enemy",
        rng=rng,
        before_guess=make_intent_revealer(rng),
        guess_resolver=find_enemy,
        answer_checker=is_correct_enemy,
        guess_limit=lambda enemy: len(get_enemy_intents(enemy)),
    )