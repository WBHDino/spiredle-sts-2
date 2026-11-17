"""Encounter guessing mode."""

from __future__ import annotations

import random

from game_common import fetch_entities, normalize, run_guessing_round


def fetch_encounters() -> list[dict]:
    return fetch_entities(
        "/api/encounters",
        predicate=lambda encounter: isinstance(encounter.get("monsters"), list)
        and bool(encounter["monsters"]),
    )


def encounter_clue_results(guess: dict, answer: dict) -> dict[str, object]:
    guess_act = guess.get("act")
    answer_act = answer.get("act")
    guess_count = len(guess.get("monsters") or [])
    answer_count = len(answer.get("monsters") or [])
    guess_tags = {normalize(str(tag)) for tag in guess.get("tags") or []}
    answer_tags = {normalize(str(tag)) for tag in answer.get("tags") or []}
    return {
        "Room": normalize(str(guess.get("room_type", "")))
        == normalize(str(answer.get("room_type", ""))),
        "Act": None if not guess_act or not answer_act else normalize(str(guess_act)) == normalize(str(answer_act)),
        "Weak": bool(guess.get("is_weak")) == bool(answer.get("is_weak")),
        "Monsters": "MATCH" if guess_count == answer_count else "UP" if guess_count < answer_count else "DOWN",
        "Tags": sorted(guess_tags & answer_tags),
    }


def print_encounter_clues(
    guess: dict,
    answer: dict,
    locked_values: dict[str, object],
) -> None:
    results = encounter_clue_results(guess, answer)
    exact_fields = {
        "Room": ("room_type", "ROOM"),
        "Act": ("act", "ACT"),
        "Weak": ("is_weak", "WEAK"),
    }
    values: dict[str, str] = {}
    for field, (key, label) in exact_fields.items():
        result = results[field]
        if result is None:
            values[label] = "NO CLUE"
        elif result:
            value = "YES" if key == "is_weak" and guess.get(key) else "NO" if key == "is_weak" else str(guess.get(key, "?"))
            locked_values.setdefault(field, value.upper())
            values[label] = str(locked_values[field])
        else:
            values[label] = "MISS"

    shared_tags = results["Tags"]
    tags_hint = ", ".join(shared_tags) if shared_tags else "none"
    print(
        f"  ROOM {values['ROOM']} | ACT {values['ACT']} | WEAK {values['WEAK']} | "
        f"MONSTERS {len(guess.get('monsters') or [])} {results['Monsters']} | SHARED TAGS {tags_hint}"
    )


def run(seed: int | None = None) -> bool:
    encounters = fetch_encounters()
    print(f"Spiredle | Encounters | {len(encounters)} encounters loaded from Spire Codex")
    return run_guessing_round(
        encounters,
        mode_name="encounter",
        rng=random.Random(seed),
        after_guess=print_encounter_clues,
    )