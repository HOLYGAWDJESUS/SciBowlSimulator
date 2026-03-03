from bot.question_base.questions_repo import Question
from typing import Optional, Iterable, List
import random

class NoQuestionsMatchError(ValueError):
    """Raised when no questions can match the critera set"""
    pass

def _normalize_set(items: Optional[Iterable[str]]) -> Optional[set[str]]:
    """Converts to uppercase in the case of mismatched casing in search
    
    None -> None
    Iterable[str] -> set[str]
    [] -> None
    e.g. {"hs", "MS"} -> {"HS", "MS"}
    """
    if items is None:
        return None
    
    normalized = set()

    for x in items:
        s = str(x).strip()
        if s:
            normalized.add(s.upper())

    return normalized if normalized else None

class QuestionPicker:
    """
    Picks a random questions from masterlist based on filters.
    """
    def __init__(self, question: List[Question], rng: Optional[random.Random] = None):
        self._questions = list(question)
        # shallow copy because my VPS is ass and doesn't have the RAM to hold multiple copies of the question list; optional if you're more wealthy.
        self._rng = rng or random.Random()

    def get_random(
        self,
        *, # I like this more
        subjects: Optional[Iterable[str]] = None,      # e.g. ["BIOLOGY", "PHYSICS", "EARTH AND SPACE (eww)"]
        qtypes: Optional[Iterable[str]] = None,        # e.g. ["SA"] or ["MC"] or ["SA","MC"]
        levels: Optional[Iterable[str]] = None,        # e.g. ["HS"] or ["MS"] or ["HS","MS"]
        bonus: Optional[bool] = None,                  # True / False / None 
        difficulties: Optional[Iterable[str]] = None,  # to be done later... (please don't forget)
    ) -> Question:
        """Returns a random question that matches all the given criteria.
           None paramater is ignored "allows any"
           Usage:
                get_random(levels=["HS"])
        """

        # Normalize into uppercase sets based on _normalize_set rules (empty preserved as None)
        subj_set = _normalize_set(subjects)
        type_set = _normalize_set(qtypes)
        level_set = _normalize_set(levels)
        diff_set = _normalize_set(difficulties)

        # DIFFICULTY IS NOT IMPLEMENTED YET, IGNORE diff_set FOR NOW
        # DIFFICULTY IS NOT IMPLEMENTED YET, IGNORE diff_set FOR NOW
        # DIFFICULTY IS NOT IMPLEMENTED YET, IGNORE diff_set FOR NOW
        # DIFFICULTY IS NOT IMPLEMENTED YET, IGNORE diff_set FOR NOW
        # DIFFICULTY IS NOT IMPLEMENTED YET, IGNORE diff_set FOR NOW

        matches: List[Question] = []
            # Scans trough question list, ignoring any criteria that are None, and collects matches.
        for q in self._questions:
            if level_set != None and (q.level or "") not in level_set:
                continue
            if subj_set != None and (q.category or "") not in subj_set: # called as q.category because questions_repo natively uses category, not subject.
                continue
            if type_set != None and (q.qtype or "") not in type_set:
                continue
            if bonus != None and bool(q.bonus) != bonus:
                continue
            matches.append(q)

        if not matches:
            raise NoQuestionsMatchError(f"No questions met the specific criteria of level={level_set}, subject={subj_set}, type={type_set}, bonus={bonus}")
        

        return self._rng.choice(matches)