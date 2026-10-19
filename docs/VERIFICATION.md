# Verification record

**Bounded release implemented, published and verified; PR #1 remains open.**
Tested implementation: `f79da0840320e822c153778c5816ccafe2b4f5d6`.
PR: https://github.com/oshada28nilendra-debug/rubrictrace/pull/1

Actual local checks: **47 tests passed, zero skips**, Ruff lint/format, compilation,
wheel build, isolated target installation and installed CLI prepare/export passed.
The installed fixture reproduced 5/5 and 1/5. Commands/logs, wheel hash and actual
installed results are in `delivery/final-checks/`; runner: scripts/verify_release.py.
The offline source demo also completed with two deliberately overridden test-double
suggestions. Both reviews are explicitly SCRIPTED fixture decisions.

Actual GitHub CI https://github.com/oshada28nilendra-debug/rubrictrace/actions/runs/39238361546
passed **47 tests, zero skips per Python 3.11/3.12/3.13**, lint/format, compile,
wheel/install and CLI demo. All three decoded logs inspected. Separate secret-scan
and real Chromium rendering jobs passed. Browser artifact (ID12179379506) was
downloaded, SHA256 `6c1468ba7376ab3d2c135edc2bc169b3d784f364d379288bea01b6fa24e0095e`
matched, and its seven actual checks were inspected. Chromium149.0.7827.55 rendered
two submissions source-first, no active elements, no mobile horizontal overflow,
correct score text, no page errors or HTTP requests. This is not a user study or
accessibility certification.

Gitleaks8.30.1 archive was SHA256-verified before execution. Local source/evidence
scans and the hosted scan passed with no findings. See delivery/gitleaks-final.json.
This is not proof of complete security or an audit of all account/provider access.

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

## Final actual inference — passed

`delivery/live-model-attempt-4/`: official Qwen3-4B Q4_K_M with checksum-verified
llama.cpp b11718, loopback CPU only. Two genuine requests, **922 prompt /171
completion tokens**, four validated suggestions. The strong answer received
clear/clear; the weak answer received partial/missing, with quotations resolved
from actual answer passages. The unchanged strong-answer gate passed. Scripted
fixture moderation exported 5/5 and 1/5. No paid API/key or real student data.

Independent hosted execution also passed:
https://github.com/oshada28nilendra-debug/rubrictrace/actions/runs/39238361771 .
Decoded logs and actual artifact were inspected. Artifact ID12180166587, SHA256
`0e110ae90b2608883bc8a6dc21eb8d8e00ddefcf637ac75be54b0dfe10d8b17d`, matched GitHub's
digest. The downloaded pack's hashes/quotes were revalidated locally, its scripted
review rerun and results compared with exported JSON. Actual responses, runtime
log, model/runtime digests, review and exports are in `delivery/github-live-model/`.

One authored fixture does not establish general grading accuracy. Three earlier
failed inference attempts remain retained. All model outputs are proposals until
explicit teacher review; the integration test's reviewer is scripted.
No paid API/key or real student data used. Teacher decisions in verification are
always SCRIPTED known-fixture decisions, not actual teacher research.

## Limits

Tests verify schemas, evidence offsets, review binding, arithmetic, output escaping,
CLI behavior and actual loopback simulated HTTP boundaries. They do not measure
pedagogy, fairness, model accuracy across real courses or production security.
Published CI and real inference results must be read from their actual logs/artifacts;
configuration files alone are not evidence they passed.
