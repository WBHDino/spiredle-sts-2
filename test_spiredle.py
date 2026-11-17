import io
import random
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from cards import clue_results, find_card, print_clues
from game_common import run_guessing_round
from enemies import (
    find_enemy,
    format_intent,
    get_enemy_intents,
    is_correct_enemy,
    make_intent_revealer,
)
from item_common import effect_terms, item_clue_results
from art import artwork_url
from card_text import staged_description
from encounters import encounter_clue_results
from daily import daily_seed, record_daily_result
from intent_order import correct_positions, get_intent_sequence, resolve_move_order
from pathlib import Path
from tempfile import TemporaryDirectory


class ClueResultsTests(unittest.TestCase):
    def setUp(self):
        self.guess = {
            "id": "GUESS",
            "name": "Guess",
            "color": "ironclad",
            "type": "Attack",
            "rarity": "Common",
            "cost": 1,
            "star_cost": 2,
        }
        self.answer = {
            "id": "ANSWER",
            "name": "Answer",
            "color": "ironclad",
            "type": "Skill",
            "rarity": "Common",
            "cost": 2,
            "star_cost": 1,
        }

    def test_exact_attributes_and_cost_directions(self):
        self.assertEqual(
            clue_results(self.guess, self.answer),
            {
                "Color": "MATCH",
                "Type": "MISS",
                "Rarity": "MATCH",
                "Cost": "UP",
                "Stars": "DOWN",
            },
        )

    def test_matching_x_costs(self):
        self.guess.update(is_x_cost=True, is_x_star_cost=True)
        self.answer.update(is_x_cost=True, is_x_star_cost=True)
        results = clue_results(self.guess, self.answer)
        self.assertEqual(results["Cost"], "MATCH")
        self.assertEqual(results["Stars"], "MATCH")

    def test_x_cost_has_no_numeric_direction(self):
        self.guess["is_x_cost"] = True
        self.assertEqual(clue_results(self.guess, self.answer)["Cost"], "NO CLUE")

    def test_rarity_clue_orders_tiers(self):
        rarities = ["Basic", "Common", "Uncommon", "Rare", "Ancient"]
        for lower, higher in zip(rarities, rarities[1:]):
            with self.subTest(lower=lower, higher=higher):
                self.guess["rarity"] = lower
                self.answer["rarity"] = higher
                self.assertEqual(clue_results(self.guess, self.answer)["Rarity"], "UP")

                self.guess["rarity"] = higher
                self.answer["rarity"] = lower
                self.assertEqual(clue_results(self.guess, self.answer)["Rarity"], "DOWN")

    def test_basic_and_starter_are_equivalent(self):
        self.guess["rarity"] = "Basic"
        self.answer["rarity"] = "Starter"
        self.assertEqual(clue_results(self.guess, self.answer)["Rarity"], "MATCH")

    def test_unranked_rarities_do_not_get_directional_clues(self):
        self.guess["rarity"] = "Event"
        self.answer["rarity"] = "Rare"
        self.assertEqual(clue_results(self.guess, self.answer)["Rarity"], "NO CLUE")

    def test_print_clues_shows_correct_values_and_wrong_field_hints(self):
        guess = {
            "color": "ironclad",
            "type": "Skill",
            "rarity": "Common",
            "cost": 2,
            "star_cost": 0,
        }
        answer = {**guess, "color": "silent"}
        output = io.StringIO()
        with redirect_stdout(output):
            print_clues(guess, answer)
        self.assertEqual(
            output.getvalue().strip(),
            "colour MISS | type SKILL | rarity COMMON | COST 2",
        )

        answer.update(type="Attack", rarity="Rare", cost=3, star_cost=1)
        output = io.StringIO()
        with redirect_stdout(output):
            print_clues(guess, answer)
        self.assertEqual(
            output.getvalue().strip(),
            "colour MISS | type MISS | rarity UP | COST UP",
        )

    def test_star_category_is_omitted_when_guess_has_no_stars(self):
        guess = {**self.guess, "star_cost": None}
        answer = {**self.answer, "star_cost": 0}
        output = io.StringIO()
        with redirect_stdout(output):
            print_clues(guess, answer)
        self.assertNotIn("STARS", output.getvalue())

    def test_correct_clue_stays_locked_on_later_guesses(self):
        answer = {
            "color": "ironclad",
            "type": "Attack",
            "rarity": "Rare",
            "cost": 2,
            "star_cost": 0,
        }
        first_guess = {**answer, "type": "Skill"}
        second_guess = {**answer, "color": "silent", "type": "Skill"}
        locked_values = {}

        output = io.StringIO()
        with redirect_stdout(output):
            print_clues(first_guess, answer, locked_values)
            print_clues(second_guess, answer, locked_values)

        lines = output.getvalue().splitlines()
        self.assertIn("colour IRONCLAD", lines[0])
        self.assertIn("colour IRONCLAD", lines[1])
        self.assertNotIn("colour MISS", lines[1])
        self.assertIn("type MISS", lines[1])

    def test_missing_star_cost_defaults_to_zero(self):
        self.answer.pop("star_cost")
        self.assertEqual(clue_results(self.guess, self.answer)["Stars"], "DOWN")

        self.guess["star_cost"] = None
        self.answer["star_cost"] = 0
        self.assertEqual(clue_results(self.guess, self.answer)["Stars"], "MATCH")

    def test_find_card_accepts_case_insensitive_name_and_id(self):
        cards = [self.guess]
        self.assertIs(find_card(cards, "  gUeSs  "), self.guess)
        self.assertIs(find_card(cards, "guess"), self.guess)
        self.assertIsNone(find_card(cards, "not a card"))

    def test_find_card_requires_id_when_names_are_duplicated(self):
        first_card = {**self.guess, "id": "GUESS_IRONCLAD"}
        second_card = {**self.guess, "id": "GUESS_SILENT", "color": "silent"}
        cards = [first_card, second_card]
        self.assertIsNone(find_card(cards, "Guess"))
        self.assertIs(find_card(cards, "GUESS_SILENT"), second_card)


class EnemyIntentTests(unittest.TestCase):
    def test_format_intent_includes_name_intent_and_effects(self):
        move = {
            "name": "Bite",
            "intent": "Attack + Debuff",
            "damage": {"normal": 7, "ascension": 8, "hit_count": 2},
            "block": 5,
            "powers": [{"power_id": "FRAIL", "target": "player", "amount": 1}],
        }
        self.assertEqual(
            format_intent(move),
            "Bite | Attack + Debuff: 7 (Asc. 8) damage x 2, 5 block, Frail 1 (player)",
        )

    def test_decimillipede_alias_resolves_and_accepts_all_segments(self):
        segments = [
            {"id": "DECIMILLIPEDE_SEGMENT_BACK", "name": "Decimillipede Segment (Back)"},
            {"id": "DECIMILLIPEDE_SEGMENT_FRONT", "name": "Decimillipede Segment (Front)"},
            {"id": "DECIMILLIPEDE_SEGMENT_MIDDLE", "name": "Decimillipede Segment (Middle)"},
        ]
        alias = find_enemy(segments, " decimillipede ")
        self.assertEqual(alias["name"], "Decimillipede")
        for segment in segments:
            with self.subTest(segment=segment["id"]):
                self.assertTrue(is_correct_enemy(alias, segment))

        self.assertFalse(is_correct_enemy(alias, {"id": "AEONGLASS", "name": "Aeonglass"}))

    def test_one_random_intent_is_revealed_per_guess_without_repeats(self):
        enemy = {
            "id": "TEST_ENEMY",
            "moves": [
                {"name": "Bite", "intent": "Attack", "damage": {"normal": 7}},
                {"name": "Roar", "intent": "Buff"},
                {"name": "Nothing", "intent": "Unknown"},
            ],
        }
        intents = get_enemy_intents(enemy)
        self.assertEqual(len(intents), 2)

        output = io.StringIO()
        reveal = make_intent_revealer(random.Random(3))
        with redirect_stdout(output):
            reveal(enemy, 1)
            reveal(enemy, 2)

        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), len(intents))
        self.assertCountEqual(
            [line.split(" | ", 1)[0].removeprefix("Intent clue: ") for line in lines],
            ["Bite", "Roar"],
        )

    def test_round_uses_mode_specific_guess_limit(self):
        class FirstChoice:
            @staticmethod
            def choice(entries):
                return entries[0]

        enemies = [
            {"id": "ANSWER", "name": "Answer"},
            {"id": "WRONG_ONE", "name": "Wrong One"},
            {"id": "WRONG_TWO", "name": "Wrong Two"},
        ]
        revealed = []
        prompt_events = []
        responses = iter(["not-an-enemy", "WRONG_ONE", "WRONG_ONE", "WRONG_TWO"])

        def fake_input(prompt):
            prompt_events.append((prompt, tuple(revealed)))
            return next(responses)

        output = io.StringIO()
        with patch("builtins.input", side_effect=fake_input) as read_input:
            with redirect_stdout(output):
                won = run_guessing_round(
                    enemies,
                    mode_name="enemy",
                    rng=FirstChoice(),
                    before_guess=lambda answer, attempt: revealed.append(attempt),
                    after_guess=lambda guess, answer, locked: revealed.append(guess["id"]),
                    guess_limit=lambda answer: 2,
                )

        self.assertFalse(won)
        self.assertEqual(read_input.call_count, 4)
        self.assertEqual(revealed, [1, "WRONG_ONE", 2, "WRONG_TWO"])
        self.assertEqual(
            prompt_events,
            [
                ("Guess 1/2: ", (1,)),
                ("Guess 1/2: ", (1,)),
                ("Guess 2/2: ", (1, "WRONG_ONE", 2)),
                ("Guess 2/2: ", (1, "WRONG_ONE", 2)),
            ],
        )


class ItemClueTests(unittest.TestCase):
    def test_relic_and_potion_clues_compare_rarity_pool_and_effect_terms(self):
        guess = {
            "rarity": "Common",
            "pool": "shared",
            "description": "At the start of combat, gain 5 block.",
        }
        answer = {
            "rarity": "Rare",
            "pool": "silent",
            "description": "At the start of each combat, gain 2 energy.",
        }

        clues = item_clue_results(guess, answer)

        self.assertFalse(clues["Rarity"])
        self.assertFalse(clues["Pool"])
        self.assertEqual(clues["Effect"], ["combat", "gain", "start"])

    def test_effect_terms_ignore_formatting_and_common_words(self):
        entity = {"description": "[gold]Deal[/gold] 5 damage to ALL enemies."}
        self.assertEqual(effect_terms(entity), {"deal", "damage", "enemies"})


class AdditionalModeTests(unittest.TestCase):
    def test_card_text_reveals_more_words_at_each_stage(self):
        description = "Deal damage then gain block and draw cards now"
        first = staged_description(description, 1, total=3)
        second = staged_description(description, 2, total=3)

        self.assertEqual(first, "Deal damage then")
        self.assertEqual(second, "Deal damage then gain block and")

    def test_card_text_preserves_star_icons_as_generic_tokens(self):
        description = "Gain 8 [gold]Block[/gold].\nGain [star:1]."
        self.assertEqual(staged_description(description, 6), "Gain 8 Block. Gain [energy/star].")

    def test_encounter_clues_compare_act_room_strength_and_roster(self):
        guess = {
            "room_type": "Monster",
            "act": "Act 1 - Overgrowth",
            "is_weak": False,
            "monsters": [{"id": "A"}],
            "tags": ["Slimes", "Workers"],
        }
        answer = {
            "room_type": "Elite",
            "act": "Act 2 - Hive",
            "is_weak": True,
            "monsters": [{"id": "B"}, {"id": "C"}],
            "tags": ["Workers"],
        }

        self.assertEqual(
            encounter_clue_results(guess, answer),
            {"Room": False, "Act": False, "Weak": False, "Monsters": "UP", "Tags": ["workers"]},
        )

    def test_artwork_uses_art_asset_not_full_render(self):
        card = {
            "image_url": "/static/images/cards/anger.webp",
            "image_url_card": "https://cdn.spire-codex.com/cards-full/stable/anger.webp",
        }
        self.assertEqual(artwork_url(card), "https://spire-codex.com/static/images/cards/anger.webp")


class IntentOrderTests(unittest.TestCase):
    def setUp(self):
        self.monster = {
            "attack_pattern": {
                "states": [
                    {"type": "move", "move_id": "BITE"},
                    {"type": "move", "move_id": "ROAR"},
                    {"type": "move", "move_id": "STOMP"},
                ]
            },
            "moves": [
                {"id": "BITE", "name": "Bite", "intent": "Attack"},
                {"id": "ROAR", "name": "Roar", "intent": "Buff"},
                {"id": "STOMP", "name": "Stomp", "intent": "Attack"},
            ],
        }

    def test_reads_move_states_in_pattern_order(self):
        self.assertEqual(
            [move["id"] for move in get_intent_sequence(self.monster)],
            ["BITE", "ROAR", "STOMP"],
        )

    def test_resolves_ids_and_scores_correct_positions(self):
        options = list(reversed(self.monster["moves"]))
        guess = resolve_move_order("BITE, ROAR, STOMP", options)
        self.assertEqual(correct_positions(guess, get_intent_sequence(self.monster)), 3)
        self.assertIsNone(resolve_move_order("Bite, Roar, Bite", options))


class DailyModeTests(unittest.TestCase):
    def test_daily_seed_is_repeatable_and_mode_specific(self):
        self.assertEqual(daily_seed("2026-06-07", "cards"), daily_seed("2026-06-07", "cards"))
        self.assertNotEqual(daily_seed("2026-06-07", "cards"), daily_seed("2026-06-07", "relics"))

    def test_daily_streak_records_once_per_day_and_resets_after_a_loss(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "stats.json"
            first, recorded = record_daily_result(path, "cards", "2026-06-05", True)
            self.assertTrue(recorded)
            self.assertEqual(first["current_streak"], 1)

            second, recorded = record_daily_result(path, "cards", "2026-06-06", True)
            self.assertTrue(recorded)
            self.assertEqual(second["current_streak"], 2)

            _, recorded = record_daily_result(path, "cards", "2026-06-06", False)
            self.assertFalse(recorded)

            third, recorded = record_daily_result(path, "cards", "2026-06-07", False)
            self.assertTrue(recorded)
            self.assertEqual(third["current_streak"], 0)
            self.assertEqual(third["best_streak"], 2)


if __name__ == "__main__":
    unittest.main()
