from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set
import re

@dataclass(frozen=True)
class CriteriaParseResult:
    picker: Dict[str, any]
    unknown_token_list: List[str] = field(default_factory=list) # Colllect common misused tokens to update accepted list

    # Check if errorlist is 0
    @property
    def accepted(self) -> bool:
        return len(self.unknown_token_list) == 0

# Expected Return Format (for other modules to use)
_CANON_LEVELS: Set[str] = {"HS", "MS"}
_CANON_QTYPES: Set[str] = {"SA", "MC"}
_CANON_SUBJECTS: Set[str] = {
    "BIOLOGY",
    "CHEMISTRY",
    "PHYSICS",
    "MATH",
    "EARTH AND SPACE",
}

# How it is displayed on embed
_DISPLAY_LEVEL = {"HS": "High School", "MS": "Middle School"}
_DISPLAY_QTYPE = {"SA": "Short Answer", "MC": "Multiple Choice"}
_DISPLAY_SUBJECT = {
    "BIOLOGY": "Biology",
    "CHEMISTRY": "Chemistry",
    "PHYSICS": "Physics",
    "MATH": "Math",
    "EARTH AND SPACE": "Earth & Space",
}

# ========
# Synonyms
# (user token -> expected return)
# (user token is normalized before comparison)
# ========


_LEVEL_SYNONYMS: Dict[str, str] = {
    "hs": "HS",
    "high": "HS",
    "highschool": "HS",
    "ms": "MS",
    "middle": "MS",
    "middleschool": "MS",
}

_QTYPE_SYNONYMS: Dict[str, str] = {
    "sa": "SA",
    "short": "SA",
    "shortanswer": "SA",
    "mc": "MC",
    "multiple": "MC",
    "multiplechoice": "MC",
    "multichoice": "MC",
}

_SUBJECT_SYNONYMS: Dict[str, str] = {
    "bio": "BIOLOGY",
    "biology": "BIOLOGY",
    "chem": "CHEMISTRY",
    "chemistry": "CHEMISTRY",
    "phys": "PHYSICS",
    "phy": "PHYSICS",
    "physics": "PHYSICS",
    "math": "MATH",
    "meth": "MATH",
    "mathematics": "MATH",
    # Earth & Space variants
    "earth": "EARTH AND SPACE",
    "es": "EARTH AND SPACE",
    "ess": "EARTH AND SPACE",
    "earthspace": "EARTH AND SPACE",
    "earthandspace": "EARTH AND SPACE",
    "earthnspace": "EARTH AND SPACE",
    "worst subject": "EARTH AND SPACE"
}

_KNOWN_TOKENS: Set[str] = set(_LEVEL_SYNONYMS) | set(_QTYPE_SYNONYMS) | set(_SUBJECT_SYNONYMS)
_BANNED_BONUS_TOKENS: Set[str] = {"bonus", "nobonus", "tossup", "tu", "b"}

##################
# Internal Helpers
##################

def _tokenize(args: str) -> List:
    '''
    Reformats the raw string by:
    Replacing , for space
    New element of list space
    Remove all elements that is just space
    '''
    cleaned: str = args.replace(",", " ")
    return [t for t in cleaned.split() if t.strip() != ""]

_NON_ALPHANUMERICAL = re.compile(r"[^a-z0-9]+")

def _normalize_token(token: str) -> str:
    '''
    lowercase
    remove non-alphanumerics
    e.g. "no-bonus" -> "nobonus", "earth&space" -> "earthspace"
    '''
    t = token.strip().lower()
    if not t:
        return ""
    return _NON_ALPHANUMERICAL.sub("", t)

def _dedupe_preserve_order(items: List[str]) -> List[str]:
    '''
    returns list in same order without dupes
    '''
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
    
def parse_criteria(args: str) -> CriteriaParseResult:
    '''
    Strict
    Any unknown token returns error
    do NOT normalize list; use it for error collection
    '''

    raw_tokens = _tokenize(args)

    levels: Set[str] = set()
    subjects: Set[str] = set()
    qtypes: Set[str] = set()

    unknown_raw: List[str] = []

    # matches criteria
    for raw in raw_tokens:
        t = _normalize_token(raw)

        if not t: # falsy value (ignore)
            continue

        if t in _BANNED_BONUS_TOKENS: # remember banned criteria usage
            unknown_raw.append(raw)

        # Checks for all matches and if not, adds to unknown raws
        if t in _LEVEL_SYNONYMS:
            levels.add(_LEVEL_SYNONYMS[t])
        elif t in _SUBJECT_SYNONYMS:
            subjects.add(_SUBJECT_SYNONYMS[t])
        elif t in _QTYPE_SYNONYMS:
            qtypes.add(_QTYPE_SYNONYMS[t])
        else:
            unknown_raw.append(raw)

    final_criteria: Dict[str, Any] = {}
    if not unknown_raw:
        if levels:
            final_criteria["levels"] = sorted(levels)
        if subjects:
            final_criteria["subjects"] = sorted(subjects)
        if qtypes:
            final_criteria["qtypes"] = sorted(qtypes)

    return CriteriaParseResult(
        picker = final_criteria,
        unknown_token_list=unknown_raw
    )
