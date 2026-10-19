# RubricTrace — bounded release design, 19 October 2026

Slot `2026-10-19-morning`. Target: teachers reviewing short typed formative answers.
Workflow: finite rubric + pseudonymous answers → optional single-model proposals
→ exact quotation/level validation → private inert report + pending JSON review
→ explicit accept/override/withhold → deterministic scores and moderation audit.
Human review is required, never inferred from model approval or a hash.

Final evidence selection: the model chooses from finite answer-passage IDs; the
engine resolves exact source quotations. Legacy literal-quote fixtures remain
accepted only after exact matching. Same source/offset/hash gates and unchanged
strong-answer smoke requirement. This narrows model generation after observed
rubric-copying failures; it does not make quotations proof of marking correctness.

Python 3.11+, stdlib only. Modules separate input/schema/evidence, HTTP/model,
review/score arithmetic and output escaping. Bounds: JSON inputs and generated
packs <=2 MB; answers <=8,000 characters; 1–8 criteria; 2–6 levels, integer points
0–100, zero minimum/positive maximum; 1–100 submissions; model <=20 requests,
24 KB context, 128 KB response, 120-second post-DNS request deadline.

Acceptance: fictional two-answer/two-criterion end-to-end run; known scores 5/5
and 1/5 after explicitly SCRIPTED fixture moderation; invented/missing/duplicate
evidence abstains; stale source/review, incomplete or invalid decisions refused;
withheld criterion suppresses whole-submission score. Unicode offsets and hostile
HTML/CSV cells handled safely; real transport tests distinct from real inference.
No runtime dependency, no model-generated code execution, no paid inference.

Select a single-model pass plus teacher moderation. Multi-agent graders would add
unvalidated complexity. Defer OCR/PDF, LMS integration, cloud identities, general
grading accuracy, calibration, pedagogy/fairness studies and high-stakes automation.

Execution plan (native): restore previously authored source; replay original tests;
reproduce/fix pack-size regression; real HTTP/model checks; independent whole-branch
review and regression-tested fixes; build/install/demo; secret scan; branch/PR;
inspect decoded CI/model evidence; record actual ledger status. No auto-merge.
