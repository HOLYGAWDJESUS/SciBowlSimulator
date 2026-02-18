import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Question:
# Immutable-ish container for a single question entry from questions.json
# Paths are resolved to local filesystem locations under images_root.
    set_name: str
    level: str
    bonus: bool
    round_name: str
    num: int
    question_image_path: Path
    answer_image_path: Path
    parsed_answer: str
    category: str
    qtype: str



class QuestionRepository:
    def __init__(self, json_filename: str = "questions.json", images_folder: str = "images"):
        # Resolve paths relative to this module file (not current working directory).
        base_dir = Path(__file__).resolve().parent

        self.json_path = base_dir / json_filename
        self.images_root = base_dir / images_folder

        print("Resolved JSON path:", self.json_path)
        print("Resolved images root:", self.images_root)

        self._questions = self._load_and_compile()

    def _load_and_compile(self) -> list[Question]:
        # Read and and parse the JSON metadata file. I want to kill myself.
        with self.json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        raw_data = data["questions"]

        compiled: list[Question] = []

        for raw in raw_data:

            level_folder = raw["level"].lower()

            question_path = self.images_root / level_folder / raw["question_image"]
            answer_path = self.images_root / level_folder / raw["answer_image"]

            compiled.append(
                Question(
                    set_name=raw["set_name"],
                    level=raw["level"],
                    bonus=raw["bonus"],
                    round_name=raw["round_name"],
                    num=raw["num"],
                    question_image_path=question_path,
                    answer_image_path=answer_path,
                    parsed_answer=raw["parsed_answer"],
                    category=raw["category"],
                    qtype=raw["type"],
                )
            )

        return compiled

    def get_all_questions(self) -> list[Question]:
        # Accessor for the preloaded question list
        return self._questions
