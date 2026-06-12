"""Lightweight heuristic classifier for bug-report / suggestion intent.

Used to detect when someone is *informally* describing a bug or posting a
suggestion in chat (rather than using the proper modal) so the bot can nudge them
toward ``/bugreport`` or ``/suggest``. Heuristics are intentionally conservative:
firing requires either a strong phrase or several weaker keyword hits, so casual
chatter doesn't get nagged.

A keyword/phrase approach is preferred over the embedding pipeline here because
intent ("I'm reporting a problem") is signalled by surface phrasing far more
reliably than by topical similarity, and it never produces a confident-but-wrong
semantic match.
"""

from __future__ import annotations

import re
from enum import Enum

# Threshold a category's score must reach to fire. A strong phrase scores 2, each
# keyword scores 1, so this means "one phrase, or at least two keywords".
_FIRE_THRESHOLD = 2


class Intent(str, Enum):
    BUG = "bug"
    SUGGESTION = "suggestion"


_BUG_PHRASES: tuple[str, ...] = (
    "doesn't work",
    "does not work",
    "doesnt work",
    "not working",
    "won't open",
    "wont open",
    "won't load",
    "wont load",
    "keeps crashing",
    "app crashes",
    "it crashes",
    "force closes",
    "force close",
    "stopped working",
    "is broken",
    "not loading",
    "can't log in",
    "cannot log in",
    "can't login",
    "white screen",
    "black screen",
    "stuck on",
)

_SUGGESTION_PHRASES: tuple[str, ...] = (
    "you should add",
    "please add",
    "can you add",
    "could you add",
    "it would be nice",
    "would be nice if",
    "i wish",
    "feature request",
    "my suggestion",
    "i suggest",
    "would love to see",
    "there should be",
    "add an option",
    "add a feature",
)

_BUG_KEYWORDS: tuple[str, ...] = (
    "bug",
    "crash",
    "crashing",
    "crashed",
    "broken",
    "error",
    "glitch",
    "freezes",
    "frozen",
    "unresponsive",
)

_SUGGESTION_KEYWORDS: tuple[str, ...] = (
    "suggestion",
    "suggest",
    "feature",
)


def _score(text: str, phrases: tuple[str, ...], keywords: tuple[str, ...]) -> int:
    score = sum(2 for phrase in phrases if phrase in text)
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            score += 1
    return score


def classify(message: str) -> Intent | None:
    """Return the detected intent, or ``None`` when nothing fires confidently."""

    text = message.lower()

    # If they already reference the proper commands, they don't need a nudge.
    if "/bugreport" in text or "/suggest" in text:
        return None

    bug = _score(text, _BUG_PHRASES, _BUG_KEYWORDS)
    suggestion = _score(text, _SUGGESTION_PHRASES, _SUGGESTION_KEYWORDS)

    if bug < _FIRE_THRESHOLD and suggestion < _FIRE_THRESHOLD:
        return None
    if bug > suggestion:
        return Intent.BUG
    if suggestion > bug:
        return Intent.SUGGESTION
    # Ambiguous (tie): stay silent rather than guess.
    return None
