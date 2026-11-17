# Spiredle

A terminal guessing game for Slay the Spire 2, backed by the Spire Codex API. Python 3.10 or newer is required; no third-party packages are used.

## Play

Run a mode from this folder:

```powershell
python main.py cards
python main.py enemies
python main.py relics
python main.py potions
python main.py card-text
python main.py encounters
python main.py intent-order
python main.py art
```

Cards gives colour, type, rarity, and cost clues. Enemies reveal one random move intent before each guess. Relics and potions compare rarity, pool, and shared effect terms. Card Text reveals more of a card's description on each valid turn. Encounters compare room, act, strength, roster size, and tags. Intent Order asks you to reconstruct the listed move-state order from a monster's attack pattern. Art Guess prints a link to the artwork-only asset, not the full rendered card image.

Use `?` during a round to repeat its prompt or `quit` to reveal the answer. Invalid entries and repeated guesses do not use a turn.

## Filters And Seeds

```powershell
python main.py cards --colour ironclad
python main.py card-text --colour silent
python main.py art --colour defect
python main.py enemies --enemy-type Elite
python main.py relics --pool silent
python main.py potions --pool shared
python main.py cards --seed 42
```

`--color` remains available as an alias for `--colour`. The first run fetches English data from `https://spire-codex.com`; an internet connection is required.

## Daily

Daily mode uses a date-and-mode seed, so players selecting the same mode on the same UTC date receive the same puzzle. It defaults to cards; choose another mode with `--daily-mode`:

```powershell
python main.py daily
python main.py daily --daily-mode relics
python main.py daily --daily-mode intent-order
```

Streaks are stored locally in `~/.spiredle/daily_stats.json`. Replaying a mode on the same date does not change its recorded streak.

## Test

```powershell
python -m unittest
```
