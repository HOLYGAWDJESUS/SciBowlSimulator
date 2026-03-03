from dataclasses import dataclass
from typing import Optional, Set, List
import re
import unicodedata


########################
# Public result type
########################

@dataclass(frozen=True)
class GradeResult:
    is_correct: bool
    reason: str  # e.g. "MC_MATCH_LETTER", "SA_EXACT_MATCH", "NO_MATCH", "EMPTY_ANSWER_KEY"
    normalized_user: str
    accepted_normalized: Set[str]
    expected_choice: Optional[str] = None  # MC correct letter if parsed, else None


########################
# Normalization
########################

_WORD_CHARS_RE = re.compile(r"[A-Z0-9]+")  # after uppercasing

def normalize_answer(text: str) -> str:
    """
    Deterministic normalization:
    - Unicode NFKD (reduces fancy characters)
    - Uppercase
    - Keep only A-Z and 0-9 tokens; punctuation becomes separators
    - Collapse to single-space tokens
    """
    if text is None:
        return ""

    # Unicode normalization to reduce fancy quotes/dashes, etc.
    text = unicodedata.normalize("NFKD", text)
    text = text.upper().strip()

    # Extract alnum tokens; punctuation becomes separators implicitly.
    tokens = _WORD_CHARS_RE.findall(text)
    return " ".join(tokens).strip()


def first_token(text_norm: str) -> str:
    if not text_norm:
        return ""
    return text_norm.split(" ", 1)[0]


########################
# Answer key parsing
########################

@dataclass(frozen=True)
class ParsedAnswerKey:
    qtype: str  # "MC" or "SA" or other
    accepted_normalized: Set[str]
    mc_letter: Optional[str] = None
    mc_text_normalized: Optional[str] = None


_MC_KEY_RE = re.compile(r"^\s*([A-Za-z])\s*[\)\.\:\-]?\s*(.*)\s*$")

def parse_mc_key(parsed_answer: str) -> ParsedAnswerKey:
    """
    Expected format examples:
      "X)  POSITIVE, NEGATIVE"
      "W. SOMETHING"
      "Y: ANSWER"
    """
    raw = (parsed_answer or "").strip()
    if not raw:
        return ParsedAnswerKey(qtype="MC", accepted_normalized=set(), mc_letter=None, mc_text_normalized=None)

    m = _MC_KEY_RE.match(raw)
    if not m:
        # fallback: treat whole key as text
        key_norm = normalize_answer(raw)
        accepted = {key_norm} if key_norm else set()
        return ParsedAnswerKey(qtype="MC", accepted_normalized=accepted, mc_letter=None, mc_text_normalized=key_norm or None)

    letter = m.group(1).upper()
    rest = (m.group(2) or "").strip()

    rest_norm = normalize_answer(rest)

    accepted: Set[str] = set()
    if letter:
        accepted.add(letter)

    if rest_norm:
        accepted.add(rest_norm)
        accepted.add(f"{letter} {rest_norm}")

    return ParsedAnswerKey(
        qtype="MC",
        accepted_normalized=accepted,
        mc_letter=letter,
        mc_text_normalized=rest_norm or None,
    )


_ACCEPT_RE = re.compile(r"ACCEPT\s*:\s*([^\)]*)", re.IGNORECASE)
_DONOT_RE = re.compile(r"DO\s*NOT\s*ACCEPT\s*:\s*([^\)]*)", re.IGNORECASE)

def _split_alternatives(raw: str) -> List[str]:
    """
    Conservative split for ACCEPT lists.
    - Prefer ';'
    - Then ' OR ' (case-insensitive)
    - Do NOT split on commas by default (commas are often part of one phrase)
    """
    s = (raw or "").strip()
    if not s:
        return []

    if ";" in s:
        parts = [p.strip() for p in s.split(";")]
        return [p for p in parts if p]

    # split on " OR " with surrounding spaces
    parts = re.split(r"\s+OR\s+", s, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) > 1 else [s]


def parse_sa_key(parsed_answer: str) -> ParsedAnswerKey:
    """
    Expected SA format examples:
    "T AND B  (ACCEPT:  B AND T CELLS)"
    "SOME ANSWER"
    Behavior:
    main answer (before first '(') is accepted
    any explicit ACCEPT: alternatives are accepted (still exact after normalization)
    any explicit DO NOT ACCEPT: alternatives are excluded if they collide
    """
    raw = (parsed_answer or "").strip()
    if not raw:
        return ParsedAnswerKey(qtype="SA", accepted_normalized=set())

    # Main answer = before first '('
    main_part = raw.split("(", 1)[0].strip()
    accepted: Set[str] = set()
    rejected: Set[str] = set()

    main_norm = normalize_answer(main_part)
    if main_norm:
        accepted.add(main_norm)

    # Look at everything inside parentheses (could be multiple)
    # We'll parse ACCEPT: and DO NOT ACCEPT: anywhere in the string.
    for match in _ACCEPT_RE.finditer(raw):
        alt_blob = match.group(1) or ""
        for alt in _split_alternatives(alt_blob):
            alt_norm = normalize_answer(alt)
            if alt_norm:
                accepted.add(alt_norm)

    for match in _DONOT_RE.finditer(raw):
        bad_blob = match.group(1) or ""
        for bad in _split_alternatives(bad_blob):
            bad_norm = normalize_answer(bad)
            if bad_norm:
                rejected.add(bad_norm)

    accepted -= rejected

    return ParsedAnswerKey(qtype="SA", accepted_normalized=accepted)


def parse_answer_key(qtype: str, parsed_answer: str) -> ParsedAnswerKey:
    qt = (qtype or "").upper().strip()

    if qt == "MC":
        return parse_mc_key(parsed_answer)
    if qt == "SA":
        return parse_sa_key(parsed_answer)

    # Fallback: strict normalized equality against the whole parsed_answer
    key_norm = normalize_answer(parsed_answer or "")
    accepted = {key_norm} if key_norm else set()
    return ParsedAnswerKey(qtype=qt or "UNKNOWN", accepted_normalized=accepted)


########################
# Grading
########################

def grade_answer(qtype: str, parsed_answer: str, user_answer: str) -> GradeResult:
    """
    Core entrypoint for Discord layer (Option B).
    """
    key = parse_answer_key(qtype, parsed_answer)
    user_norm = normalize_answer(user_answer or "")

    if not (parsed_answer or "").strip():
        return GradeResult(
            is_correct=False,
            reason="EMPTY_ANSWER_KEY",
            normalized_user=user_norm,
            accepted_normalized=set(),
            expected_choice=None,
        )

    # MC grading rules
    if key.qtype == "MC":
        # If we successfully parsed the correct letter, allow:
        # - first token == correct letter (and anything after)  [your "W and then whatever"]
        # - exact matches against accepted set (letter alone, text alone, letter+text)
        if key.mc_letter:
            if first_token(user_norm) == key.mc_letter:
                return GradeResult(
                    is_correct=True,
                    reason="MC_MATCH_LETTER_PREFIX",
                    normalized_user=user_norm,
                    accepted_normalized=set(key.accepted_normalized),
                    expected_choice=key.mc_letter,
                )

        if user_norm and user_norm in key.accepted_normalized:
            return GradeResult(
                is_correct=True,
                reason="MC_EXACT_MATCH",
                normalized_user=user_norm,
                accepted_normalized=set(key.accepted_normalized),
                expected_choice=key.mc_letter,
            )

        return GradeResult(
            is_correct=False,
            reason="NO_MATCH",
            normalized_user=user_norm,
            accepted_normalized=set(key.accepted_normalized),
            expected_choice=key.mc_letter,
        )

    # SA grading rules (strict exact after normalization)
    if key.qtype == "SA":
        if user_norm and user_norm in key.accepted_normalized:
            return GradeResult(
                is_correct=True,
                reason="SA_EXACT_MATCH",
                normalized_user=user_norm,
                accepted_normalized=set(key.accepted_normalized),
                expected_choice=None,
            )

        return GradeResult(
            is_correct=False,
            reason="NO_MATCH",
            normalized_user=user_norm,
            accepted_normalized=set(key.accepted_normalized),
            expected_choice=None,
        )

    # Fallback grading (strict normalized equality vs accepted set)
    if user_norm and user_norm in key.accepted_normalized:
        return GradeResult(
            is_correct=True,
            reason="FALLBACK_EXACT_MATCH",
            normalized_user=user_norm,
            accepted_normalized=set(key.accepted_normalized),
            expected_choice=None,
        )

    return GradeResult(
        is_correct=False,
        reason="NO_MATCH",
        normalized_user=user_norm,
        accepted_normalized=set(key.accepted_normalized),
        expected_choice=None,
    )