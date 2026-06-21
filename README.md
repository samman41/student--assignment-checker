# student--assignment-checker
A repository for the AI-Based Student Assignment Checker Workflow Project
--Scope--
One narrow task: before grading a batch of short written assignments (e.g. a 150–800 word
reflection or essay), automatically check each submission against a rubric and flag
problems for the grader instead of catching them by eye. The tool checks word count,
required sections, citation presence, similarity to past submissions, basic grammar
issues, and gets qualitative AI feedback. It's a first-pass filter, not a
replacement for the grader.

--Run this every time you check a batch
1.Collect all submissions as plain text files (.txt) in one folder — convert from
Word/PDF first if needed.
2.For each submission run:
python assignment_checker.py --file submission_name.txt --rubric rubric.json --corpus-dir reference_corpus --output reports/submission_name_report.json
3.Read the printed PASS/FAIL summary in the terminal. Anything marked FAIL needs a look
before grading.
4.Pay special attention to the Similarity check — a FAIL means high overlap with a past
submission and should be manually reviewed, not auto-flagged as cheating.
5.If you want AI written feedback on content quality/clarity, add --use-ai to the
command .
6.After reviewing, copy the checked submission into reference_corpus/ so future
submissions get compared against it too.
7.Move on to the next submission and repeat from step 2.

