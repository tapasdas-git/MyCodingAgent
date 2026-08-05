from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from .schemas import (
    FormattedLLMPrompt,
    RawPrompt,
    RedactionRecord,
    SanitizedPrompt,
    SystemMessage,
    UserMessage,
)

EnvGetter = Callable[[str, str | None], str | None]

DEFAULT_SYSTEM_PROMPT = (
    "You are a prompt optimization assistant. Preserve the user's intent while "
    "removing secrets and personally identifying information."
)

EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w.-])"
)
CREDIT_CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}\d(?!\d)")
API_KEY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key", re.compile(r"(?<![\w-])(sk-[A-Za-z0-9-]{20,})(?![\w-])")),
    ("api_key", re.compile(r"(?<![\w-])(gh[pousr]_[A-Za-z0-9]{20,})(?![\w-])")),
    ("api_key", re.compile(r"(?<![\w-])(xox[baprs]-[A-Za-z0-9-]{10,})(?![\w-])")),
    (
        "api_key",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*([A-Za-z0-9/_=-]{8,})"
        ),
    ),
)


@dataclass(frozen=True)
class _Match:
    start: int
    end: int
    kind: str
    value: str

    @property
    def placeholder(self) -> str:
        return f"[REDACTED_{self.kind.upper()}]"


class PromptOptimizer:
    def __init__(
        self,
        *,
        prompt_opt_key: str | None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._prompt_opt_key = prompt_opt_key.strip() if prompt_opt_key else None
        self._system_prompt = system_prompt.strip()
        if not self._system_prompt:
            raise ValueError("system_prompt must not be blank")

    @property
    def prompt_opt_key(self) -> str | None:
        return self._prompt_opt_key

    def sanitize(self, raw_prompt: RawPrompt) -> SanitizedPrompt:
        text = raw_prompt.text
        matches = list(self._find_matches(text))
        if not matches:
            return SanitizedPrompt(
                original_text=text,
                sanitized_text=text,
                redactions=[],
            )

        sanitized_text = self._apply_matches(text, matches)
        redactions = [
            RedactionRecord(kind=match.kind, placeholder=match.placeholder, value=match.value)
            for match in matches
        ]
        return SanitizedPrompt(
            original_text=text,
            sanitized_text=sanitized_text,
            redactions=redactions,
        )

    def format(self, sanitized_prompt: SanitizedPrompt) -> FormattedLLMPrompt:
        redaction_summary = self._summarize_redactions(sanitized_prompt.redactions)
        system_content = self._system_prompt
        if redaction_summary:
            system_content = f"{system_content}\n\n{redaction_summary}"
        if self._prompt_opt_key:
            system_content = f"{system_content}\nPrompt optimization key loaded."

        return FormattedLLMPrompt(
            system_message=SystemMessage(content=system_content),
            user_message=UserMessage(content=sanitized_prompt.sanitized_text),
            prompt_opt_key=self._prompt_opt_key,
        )

    def optimize(self, raw_prompt: RawPrompt) -> FormattedLLMPrompt:
        return self.format(self.sanitize(raw_prompt))

    def _find_matches(self, text: str) -> Iterable[_Match]:
        matches: list[_Match] = []

        for match in EMAIL_PATTERN.finditer(text):
            matches.append(_Match(match.start(1), match.end(1), "email", match.group(1)))

        for kind, pattern in API_KEY_PATTERNS:
            for match in pattern.finditer(text):
                group_index = 1 if match.lastindex else 0
                matches.append(
                    _Match(
                        match.start(group_index),
                        match.end(group_index),
                        kind,
                        match.group(group_index),
                    )
                )

        for match in CREDIT_CARD_PATTERN.finditer(text):
            candidate = re.sub(r"[ -]", "", match.group(0))
            if _is_luhn_valid(candidate):
                matches.append(
                    _Match(match.start(0), match.end(0), "credit_card", match.group(0))
                )

        return _deduplicate_and_sort(matches)

    def _apply_matches(self, text: str, matches: Sequence[_Match]) -> str:
        parts: list[str] = []
        cursor = 0
        for match in matches:
            parts.append(text[cursor:match.start])
            parts.append(match.placeholder)
            cursor = match.end
        parts.append(text[cursor:])
        return "".join(parts)

    def _summarize_redactions(self, redactions: Sequence[RedactionRecord]) -> str:
        if not redactions:
            return ""

        counts: dict[str, int] = {}
        for redaction in redactions:
            counts[redaction.kind] = counts.get(redaction.kind, 0) + 1

        summary_bits = ", ".join(
            f"{count} {kind.replace('_', ' ')}" for kind, count in sorted(counts.items())
        )
        return f"Redaction summary: {summary_bits} removed."


def create_prompt_optimizer(
    *,
    env_getter: EnvGetter = os.getenv,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> PromptOptimizer:
    prompt_opt_key = env_getter("PROMPT_OPT_KEY", None)
    return PromptOptimizer(prompt_opt_key=prompt_opt_key, system_prompt=system_prompt)


def _deduplicate_and_sort(matches: Sequence[_Match]) -> list[_Match]:
    ordered = sorted(matches, key=lambda item: (item.start, item.end, item.kind, item.value))
    deduplicated: list[_Match] = []
    last_span: tuple[int, int, str] | None = None
    for match in ordered:
        span = (match.start, match.end, match.kind)
        if last_span == span:
            continue
        if deduplicated and match.start < deduplicated[-1].end:
            if match.end <= deduplicated[-1].end:
                continue
            raise ValueError("overlapping redaction spans are not supported")
        deduplicated.append(match)
        last_span = span
    return deduplicated


def _is_luhn_valid(number: str) -> bool:
    if not number.isdigit() or not 13 <= len(number) <= 19:
        return False

    total = 0
    double = False
    for digit_char in reversed(number):
        digit = int(digit_char)
        if double:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        double = not double
    return total % 10 == 0
