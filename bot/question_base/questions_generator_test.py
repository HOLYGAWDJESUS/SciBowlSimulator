from questions_repo import QuestionRepository
from questions_generator import QuestionPicker

repo = QuestionRepository()
picker = QuestionPicker(repo.get_all_questions())

def show_question(label, q):
    print(f"\n=== {label} ===")
    print("Set:", q.set_name)
    print("Level:", q.level)
    print("Round:", q.round_name)
    print("Num:", q.num)
    print("Category:", q.category)
    print("Type:", q.qtype)
    print("Bonus:", q.bonus)
    print("Parsed Answer:", q.parsed_answer)

    print("Question image path:", q.question_image_path)
    print("Answer image path:", q.answer_image_path)
    print("Question image exists?", q.question_image_path.exists())
    print("Answer image exists?", q.answer_image_path.exists())

q1 = picker.get_random()
show_question("Any", q1)

q2 = picker.get_random(levels=["HS"], qtypes=["SA"], bonus=False)
show_question("HS SA non-bonus", q2)

q3 = picker.get_random(subjects=["PHYSICS", "CHEMISTRY"])
show_question("Physics/Chem", q3)