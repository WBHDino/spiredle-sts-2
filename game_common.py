"""Shared API access and guessing-round flow for Spiredle modes."""

from __future__ import annotations

import json
import random
import re
from collections.abc import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://spire-codex.com"
MAX_GUESSES = 6


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def fetch_entities(
    endpoint: str,
    params: dict[str, str] | None = None,
    predicate: Callable[[dict], bool] | None = None,
) -> list[dict]:
    query = {"lang": "eng", **(params or {})}
    request = Request(
        f"{API_URL}{endpoint}?{urlencode(query)}",
        headers={"User-Agent": "Spiredle/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    if not isinstance(payload, list):
        raise ValueError(f"The {endpoint.rsplit('/', 1)[-1]} API returned an unexpected response.")

    entities = [
        entity
        for entity in payload
        if isinstance(entity, dict)
        and entity.get("id")
        and entity.get("name")
        and (predicate is None or predicate(entity))
    ]
    if not entities:
        raise ValueError("The API did not return any playable entries for this selection.")
    return entities


def find_entity(entities: list[dict], query: str) -> dict | None:
    normalized = normalize(query)
    id_matches = [entity for entity in entities if normalized == normalize(str(entity["id"]))]
    if id_matches:
        return id_matches[0]
    name_matches = [entity for entity in entities if normalized == normalize(str(entity["name"]))]
    return name_matches[0] if len(name_matches) == 1 else None


def run_guessing_round(
    entities: list[dict],
    *,
    mode_name: str,
    rng: random.Random,
    round_clues: Callable[[dict], None] | None = None,
    before_guess: Callable[[dict, int], None] | None = None,
    after_guess: Callable[[dict, dict, dict[str, object]], None] | None = None,
    guess_resolver: Callable[[list[dict], str], dict | None] | None = None,
    answer_checker: Callable[[dict, dict], bool] | None = None,
    guess_limit: Callable[[dict], int] | None = None,
) -> bool:
    answer = rng.choice(entities)
    max_guesses = max(1, guess_limit(answer)) if guess_limit else MAX_GUESSES
    guessed_ids: set[str] = set()
    locked_values: dict[str, object] = {}
    print(f"\nA random Slay the Spire 2 {mode_name} is ready. Type ? for rules.\n")
    if round_clues:
        round_clues(answer)

    revealed_attempt = 0
    while len(guessed_ids) < max_guesses:
        attempt = len(guessed_ids) + 1
        if before_guess and attempt != revealed_attempt:
            before_guess(answer, attempt)
            revealed_attempt = attempt
        try:
            query = input(f"Guess {attempt}/{max_guesses}: ").strip()
        except EOFError:
            print("\nRound ended.")
            return False

        if not query:
            continue
        if normalize(query) in {"quit", "exit"}:
            print(f"The {mode_name} was {answer['name']} ({answer['id']}).")
            return False
        if query == "?":
            print(f"Guess an exact name or API ID. You have {max_guesses} valid guesses; type quit to exit.")
            continue

        guess = (
            guess_resolver(entities, query)
            if guess_resolver
            else find_entity(entities, query)
        )
        if guess is None:
            name_matches = [
                entity for entity in entities
                if normalize(str(entity["name"])) == normalize(query)
            ]
            if len(name_matches) > 1:
                ids = ", ".join(str(entity["id"]) for entity in name_matches)
                print(f"That name belongs to multiple entries. Guess by ID: {ids}")
                continue
            suggestions = [
                f"{entity['name']} [{entity['id']}]"
                for entity in entities
                if normalize(str(entity["name"])).startswith(normalize(query))
            ][:6]
            if suggestions:
                print("No exact match. Did you mean: " + ", ".join(suggestions) + "?")
            else:
                print("No entry found by that name or ID.")
            continue

        entity_id = str(guess["id"])
        if entity_id in guessed_ids:
            print("You already guessed that entry; it does not use a turn.")
            continue
        guessed_ids.add(entity_id)

        if after_guess:
            after_guess(guess, answer, locked_values)
        is_correct = (
            answer_checker(guess, answer)
            if answer_checker
            else entity_id == str(answer["id"])
        )
        if is_correct:
            print(f"Correct! {answer['name']} in {len(guessed_ids)} guess(es).")
            return True
        if after_guess is None:
            print("Not that entry.")

    print(f"Out of guesses. The {mode_name} was {answer['name']} ({answer['id']}).")
    return False