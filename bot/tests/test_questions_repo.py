from bot.question_base.questions_repo import QuestionRepository

repo = QuestionRepository()

list: questions

questions = repo.get_all_questions()

print("Loaded totl amt of qs:", len(questions))

q = questions[0]

print("Question path:", q.question_image_path)
print("Exists boolean:", q.question_image_path.exists())
