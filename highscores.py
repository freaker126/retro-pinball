"""
=============================================================================
highscores.py - High Score Leaderboard & Persistence Manager
=============================================================================
Educational Note:
Persistent Data Storage in Python:
Games need to save player progress and high scores across play sessions.
JSON (JavaScript Object Notation) is the ideal human-readable format for this:
  - It maps directly to Python's native `dict`, `list`, `str`, and `int` types.
  - It can be inspected or edited by students using any standard text editor.
  - Python's built-in `json` module provides `json.dump()` (serialize to file)
    and `json.load()` (deserialize from file).

Defensive Programming:
Never assume an external data file exists or is uncorrupted. If a file is
deleted, locked, or contains malformed JSON, our code must gracefully catch
the exception (`FileNotFoundError`, `json.JSONDecodeError`) and fall back to
sensible default high scores rather than crashing the game.
=============================================================================
"""

import json
from datetime import datetime
from pathlib import Path

from constants import HIGHSCORES_FILE


# Default arcade high scores for nostalgic arcade flavor
DEFAULT_HIGH_SCORES = [
    {"name": "ACE", "score": 75000, "date": "1982-10-01"},
    {"name": "NEO", "score": 50000, "date": "1983-05-15"},
    {"name": "MAX", "score": 35000, "date": "1984-11-20"},
    {"name": "PIN", "score": 25000, "date": "1985-02-14"},
    {"name": "RET", "score": 15000, "date": "1986-08-08"},
    {"name": "BOB", "score": 10000, "date": "1987-12-25"},
    {"name": "LIZ", "score": 7500,  "date": "1988-04-01"},
    {"name": "DAN", "score": 5000,  "date": "1989-07-04"},
]

MAX_LEADERBOARD_ENTRIES = 8


class HighScoreManager:
    """
    Manages loading, validating, updating, and saving the Top Scores leaderboard.
    """
    def __init__(self, filepath: Path = HIGHSCORES_FILE):
        self.filepath = filepath
        self.scores: list[dict] = []
        self.load()

    def load(self):
        """
        Loads scores from JSON file. If file is missing or invalid, initializes defaults.
        """
        if not self.filepath.exists():
            self.scores = list(DEFAULT_HIGH_SCORES)
            self.save()
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    # Sanitize and validate loaded entries
                    cleaned = []
                    for item in data:
                        if isinstance(item, dict) and "name" in item and "score" in item:
                            cleaned.append({
                                "name": str(item["name"])[:3].upper(),
                                "score": int(item["score"]),
                                "date": str(item.get("date", datetime.now().strftime("%Y-%m-%d")))
                            })
                    cleaned.sort(key=lambda x: x["score"], reverse=True)
                    self.scores = cleaned[:MAX_LEADERBOARD_ENTRIES]
                else:
                    self.scores = list(DEFAULT_HIGH_SCORES)
                    self.save()
        except (json.JSONDecodeError, OSError, ValueError) as e:
            print(f"[HighScoreManager] Error reading high scores ({e}). Restoring defaults.")
            self.scores = list(DEFAULT_HIGH_SCORES)
            self.save()

    def save(self):
        """Saves current leaderboard entries to the JSON file with clean indentation."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.scores, f, indent=2)
        except OSError as e:
            print(f"[HighScoreManager] Failed to write high scores to disk: {e}")

    def is_high_score(self, score: int) -> bool:
        """
        Returns True if the given score qualifies for the leaderboard.
        Educational Note:
        A score qualifies if either:
          1. The leaderboard has not reached its maximum capacity.
          2. The score is strictly greater than the lowest score on the board.
        """
        if score <= 0:
            return False
        if len(self.scores) < MAX_LEADERBOARD_ENTRIES:
            return True
        return score > self.scores[-1]["score"]

    def add_score(self, name: str, score: int) -> int:
        """
        Inserts a new score, sorts in descending order, and trims to max entries.
        Returns the 1-based rank achieved (e.g. 1 for #1 Grand Champion).
        """
        sanitized_name = (name.strip().upper() or "AAA")[:3]
        today_str = datetime.now().strftime("%Y-%m-%d")
        new_entry = {
            "name": sanitized_name,
            "score": int(score),
            "date": today_str
        }

        self.scores.append(new_entry)
        # Sort descending by score
        self.scores.sort(key=lambda entry: entry["score"], reverse=True)
        # Keep only top entries
        self.scores = self.scores[:MAX_LEADERBOARD_ENTRIES]
        self.save()

        # Find 1-based index rank of new entry
        for idx, entry in enumerate(self.scores):
            if entry is new_entry:
                return idx + 1
        return len(self.scores)

    def get_top_score(self) -> int:
        """Returns the highest score on record, or 0 if empty."""
        if self.scores:
            return self.scores[0]["score"]
        return 0
