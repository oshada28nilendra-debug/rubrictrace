# Verification record

Release verification is in progress. Current actual local result: **44 tests
passed, zero skipped**, Ruff lint/format passed, offline scripted CLI fixture
completed with scores 5/5 and 1/5 and two overrides. Wheel build passed before the
last JSON-boundary fix; final build/install and hosted CI are being repeated.
This intermediate paragraph will be superseded by the final release record.

## Real model attempts retained

`delivery/live-model-attempt-1/`: checksum-pinned llama.cpp b11718 and official
Qwen3-1.7B Q8_0, two actual requests, 806 prompt /259 completion tokens. Three
suggestions passed structural evidence gates; a fourth quoted a rubric descriptor
instead of the answer and was rejected. The model incorrectly awarded a positive
mitigation level for an ineffective answer. Strong-answer smoke gate FAILED.

`delivery/live-model-attempt-2/`: same runtime/model, clarified quotation/descriptor
prompt; two actual requests, 964 prompt /216 completion tokens. One validated
suggestion, three abstentions (including a relevant strong-answer cause). Strong-
answer smoke gate FAILED. No claim this model correctly grades all criteria.

The final local-model check uses separately pinned official Qwen3-4B Q4_K_M.
Attempt 3 used that model with free-form quotations: two calls, 964 prompt /160
completion tokens; two validated suggestions. It again quoted a rubric descriptor
for the strong cause, so its smoke gate FAILED. Preserved in delivery/.
The adapter now asks the model to select finite answer-passage IDs. Code resolves
the selected passage to exact answer text and retains the same quote/hash checks.
Unknown evidence IDs abstain; legacy quote fixtures remain supported. This is an
engineering change to evidence selection, not a relaxed strong-answer smoke gate.
No paid API/key or real student data used. Teacher decisions in verification are
always SCRIPTED known-fixture decisions, not actual teacher research.

## Limits

Tests verify schemas, evidence offsets, review binding, arithmetic, output escaping,
CLI behavior and actual loopback simulated HTTP boundaries. They do not measure
pedagogy, fairness, model accuracy across real courses or production security.
Published CI and real inference results must be read from their actual logs/artifacts;
configuration files alone are not evidence they passed.
