# SciBowlSimulator
A Discord Science Bowl practice bot that posts question **images**, accepts answers, and tracks points + stats with **SQLite** based storage.

<p align="center">
  <a href="https://github.com/HOLYGAWDJESUS/SciBowlSimulator">
    <img src="https://img.shields.io/badge/BUILD-PASSING-brightgreen?style=for-the-badge" />
  </a>
  <a href="https://discord.com/oauth2/authorize?client_id=1478271437721698368&permissions=460800&integration_type=0&scope=bot">
    <img src="https://img.shields.io/badge/INVITE-BOT-5865F2?style=for-the-badge&logo=discord&logoColor=white" />
  </a>
  <img src="https://img.shields.io/badge/PYTHON-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/STATUS-ALPHA-orange?style=for-the-badge" />
</p>

**Progress:**

- ~~Question Generation of Question Object~~
- ~~Memory storage for active/passive channels~~
- ~~Memory storage for disabled channels~~
- ~~Session Manager~~
- ~~Exceptions for question errors~~
- ~~Criteria Interpeter to normalize and generate **criteria~~
- ~~Answer grader~~
- ~~Discord handler and builter~~
- ~~Public commands~~

**TODOs:**


- Admin Commands
- Bonus Question Generation
- Store disabled channels in storage instead of memory
- **AI Grading for SA Questions**
- Add Difficulty criteria based on round selections

---

## What it does
- Posts Science Bowl questions as **image attachments**
- Keeps gameplay **simple** and without f*ckass annoying slash commands:
  - `-q` posts a question (or re-posts the current one)
  - `-a <answer>` attempts an answer (**first attempt ends the question**)
- Tracks persistence via SQLite:
  - player points
  - total questions generated
  - disabled channels
  - per-question attempts/correct (solve rate) *used in debugging incorrectly json scrape.

---

## Commands
### `-q [criteria...]`
Posts a question image in the current channel. In the form of an embed, restating the interpreted criteria.

**Usage**:
- If there is **no active question** in the channel → selects a new one and posts it.
- If there **is** an active question → re-posts the same question. 

**Criteria Options**:
- Subjects: `math`, `chemistry`, `biology`, `earth and space`, `physics`
- Levels: `highschool`, `middleschool` (add prometheus rounds later)
- Question Types: `shortanswer`, `mutiplechoice`

No any category left blank is assumed to include all options. E.g. no subject selection means all subject questions can be returned. You can use mutiple criterias to indicate you want a random question from more than one choice. Order of arguements do not matter.

Examples:
- `-q` - all questions could be returned
- `-q hs bio sa` - highschool round, biology, short answer
- `-q bio chem` - biology or chemistry question

### `-a <answer>`
Submits an answer to the current active questions within the channel.

**Rules:**
- The **first** `-a` attempt ends the question immediately (whether correct or incorrect).
- If correct → +1 point to that user. (will be based on correct science bowl point system once bonus are added)
- Bot reveals the official answer (answer image and parsed answer text---includes all accepted options for SA).


**Multiple Choice Accepts:**

Key: `W) Mass Spectrometry`
1. The corrosponding letter e.g. `W`
2. The arguement e.g. `Mass Spectrometry`
3. The corrosponding letter and arguement `W Mass Spectrometry`

**Short Answer Accepts:**

Key: `URANIUM-238 (ACCEPT: 238)`
1. Token(s) before parathenesis e.g. `URANIUM-238`
2. Accepted Token(s) after parathensis (must have ACCEPT: before it) e.g. `238`

Note: capiltaization and seperators do not matter. 

---

## Data source (questions)
expects:
- **metadata** JSON (e.g. `questions.json`)

`{
"set_name": "Sample-Set-1",
"level": "HS",
"bonus": false,
"round_name": "round1",
"num": 0,
"question_image": "Sample-Set-1/round1/1_0.png",
"page": 1,
"parsed_answer": "PHENOTYPE",
"answer_image": "Sample-Set-1/round1/1_0_ans.png",
"category": "BIOLOGY",
"type": "SA"
},`


- **question/answer images** on disk

![examplequestion](https://files.catbox.moe/2me5u6.png)
![examplequestion](https://files.catbox.moe/bkb0io.png)

(Actual png has transparent background.)

Credit for original questions images: `arxenix/Scibowl_Questions`.

### Expected layout
Your loader resolves paths relative to the question-base module folder. Put these together:

<p align="center">
Made with ❤️ by <a href="https://github.com/HOLYGAWDJESUS">Shulin Lu</a>
</p>
