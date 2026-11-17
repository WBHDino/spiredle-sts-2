"""Spiredle command-line mode launcher."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError

import art
import card_text
import cards
import daily
import encounters
import enemies
import intent_order
import potions
import relics

MODES = (
    "cards",
    "enemies",
    "relics",
    "potions",
    "card-text",
    "encounters",
    "intent-order",
    "art",
    "daily",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a Slay the Spire 2 guessing game.")
    parser.add_argument("mode", choices=MODES, help="game mode to play")
    parser.add_argument("--colour", "--color", dest="color", help="card modes: limit the pool to a card colour")
    parser.add_argument("--enemy-type", choices=("Normal", "Elite", "Boss"), help="enemy mode: limit enemy type")
    parser.add_argument("--pool", help="relic or potion mode: limit the pool")
    parser.add_argument("--daily-mode", choices=daily.DAILY_MODES, help="daily mode: choose which game to play")
    parser.add_argument("--seed", type=int, help="use a repeatable random seed")
    args = parser.parse_args()

    try:
        if args.mode == "daily":
            if args.color or args.enemy_type or args.pool or args.seed is not None:
                parser.error("daily mode uses its own shared seed and does not accept filters")
            daily.run(args.daily_mode or "cards")
        else:
            if args.daily_mode:
                parser.error("--daily-mode is only available with daily mode")
            if args.mode in {"cards", "card-text", "art"}:
                if args.enemy_type or args.pool:
                    parser.error("--enemy-type and --pool are not available in card modes")
                if args.mode == "cards":
                    cards.run(color=args.color, seed=args.seed)
                elif args.mode == "card-text":
                    card_text.run(color=args.color, seed=args.seed)
                else:
                    art.run(color=args.color, seed=args.seed)
            elif args.mode == "enemies":
                if args.color or args.pool:
                    parser.error("--colour and --pool are not available in enemy mode")
                enemies.run(enemy_type=args.enemy_type, seed=args.seed)
            elif args.mode in {"relics", "potions"}:
                if args.color or args.enemy_type:
                    parser.error("--colour and --enemy-type are not available in relic or potion modes")
                if args.mode == "relics":
                    relics.run(pool=args.pool, seed=args.seed)
                else:
                    potions.run(pool=args.pool, seed=args.seed)
            elif args.mode == "encounters":
                if args.color or args.enemy_type or args.pool:
                    parser.error("filters are not available in encounter mode")
                encounters.run(seed=args.seed)
            else:
                if args.color or args.enemy_type or args.pool:
                    parser.error("filters are not available in intent-order mode")
                intent_order.run(seed=args.seed)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        print(f"Could not load game data from Spire Codex: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())