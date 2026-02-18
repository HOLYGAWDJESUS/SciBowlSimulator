from question_base.questions_repo import QuestionRepository
from questions import QuestionPicker

repo = QuestionRepository()
picker = QuestionPicker(repo.get_all_questions())

q1 = picker.get_random()
print("Any:", q1.level, q1.qtype, q1.category, q1.bonus)
print("Path exists?", q1.question_image_path.exists())

q2 = picker.get_random(levels=["HS"], qtypes=["SA"], bonus=False)
print("HS SA non-bonus:", q2.level, q2.qtype, q2.category, q2.bonus)

q3 = picker.get_random(subjects=["PHYSICS", "CHEMISTRY"])
print("Physics/Chem:", q3.category, q3.level, q3.qtype)