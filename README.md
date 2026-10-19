# RubricTrace

**Review AI feedback against the student's actual words before deciding a mark.**

A local-first tool for teachers and teaching assistants reviewing short, typed
formative answers. It separates model suggestions, exact evidence and teacher
decisions, then calculates scores deterministically. Python 3.11+, no runtime
package dependencies.

## Contents

- [Workflow](#workflow)
- [Install and try](#install-and-try)
- [Use real AI](#use-real-ai)
- [Review decisions](#review-decisions)
- [Input and scoring](#input-and-scoring)
- [Commands and outputs](#commands-and-outputs)
- [Privacy and limits](#privacy-and-limits)
- [Architecture and development](#architecture-and-development)
- [Verification and license](#verification-and-license)

## Workflow

1. Import a JSON prompt, explicit rubric and pseudonymous submissions.
2. Prepare manual review or ask a real compatible model for finite rubric-level
   suggestions, an exact answer quotation and a reason.
3. Inspect original answers **before** suggestions in a private inert HTML report.
   Invented quotes, duplicate criteria and invalid levels abstain.
4. Edit JSON decisions: accept, override with a note, or withhold. Write your own
   student feedback; a model cannot approve itself.
5. Confirm the reviewed pack. Recheck the original input and export deterministic
   scores, teacher feedback and a moderation audit.

An exact quote proves where text occurs, **not** that the assessment is correct.
This supports formative review, not autonomous high-stakes grading.

## Install and try

From the repository root (Windows, Linux or macOS with Python 3.11+):

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
rubrictrace prepare fixtures/assessment.json --out work/manual
```

Open `work/manual/review.html` locally. Copy `review-template.json` to
`review.json` and edit it. Manual mode makes no model calls and leaves all
criteria unreviewed.

For a complete scripted demonstration, using fictional data and **no real teacher**:

```bash
python scripts/demo.py --out work/demo
```

Expected fixture results: S001 = 5/5 (100.00%), S002 = 1/5 (20.00%). Two deliberately
generous test-double suggestions are overridden by scripted fixture decisions.
This demonstrates orchestration, not AI grading accuracy.

## Use real AI

Start your own Chat Completions-compatible server, then use its model name/base URL:

```bash
rubrictrace prepare fixtures/assessment.json --model your-model --endpoint http://127.0.0.1:18082/v1 --max-calls 2 --out work/ai
```

For a reproducible key-free Linux CPU check, the optional helper downloads a
checksum-pinned llama.cpp runtime and official Qwen3-4B Q4_K_M weights (~2.5 GB).
The downloader needs Python 3.12+ for safe archive extraction:

```bash
python scripts/download_model.py --out model-cache
python scripts/live_smoke.py --runtime-root model-cache --out work/live
```

The smoke starts/stops its own loopback server, invokes the actual adapter twice,
checks exact evidence for the strong fictional answer, then completes export
using clearly **SCRIPTED** fixture moderation. See actual results and failed
earlier 1.7B attempts in [verification](docs/VERIFICATION.md). No weights are bundled.

For a remote provider, set `RUBRICTRACE_API_KEY` in your process environment and
add `--allow-remote-model --endpoint https://YOUR-PROVIDER/v1`. This permits sending
the prompt, rubric and answer to that provider; fees and its data policies apply.
No paid inference is used in release verification. `.env.example` documents the
variable; the CLI does not automatically load `.env` files. Never put keys in URLs.

## Review decisions

Each entry in `review-template.json` identifies a submission and criterion:

```json
{
  "submission_id": "S002",
  "criterion_id": "cause",
  "action": "override",
  "level": "partial",
  "feedback": "You identified retry. Explain how a lost acknowledgement causes it.",
  "note": "The response mentions retry but not the acknowledgement mechanism."
}
```

Decide **every** criterion, supply a reviewer alias and set `confirmed` to `true`
only after review. Keep the generated `pack_digest` unchanged.

| Action | Rule |
| --- | --- |
| `pending` | Default; export refused |
| `accept` | Unchanged validated suggestion; teacher feedback required |
| `override` | Valid rubric level, teacher feedback and a nonempty note |
| `withhold` | `level: null`, note required; entire submission receives no score |

```bash
rubrictrace export --assessment fixtures/assessment.json --pack work/ai/pack.json --review work/ai/review.json --out work/final
```

Hashes catch changed content and stale reviews. They are **not signatures**, identity
verification or proof that someone read the work. Anyone who changes all files and
recomputes their hashes can forge an audit. Use a trusted private directory.

## Input and scoring

See `fixtures/assessment.json` for the complete schema. Version `schema: 1` takes
a title, prompt, rubric and submissions. Each criterion has an opaque ID,
description and 2–6 levels with ID, description and integer points 0–100. Each
criterion requires a zero level and positive maximum. Use 1–8 criteria, 1–100
submissions and at most 8,000 characters per answer. IDs preserve leading zeros
but must start alphanumerically and contain only letters, digits, `_`, `.` or `-`.
Use pseudonyms; do not include a roster or real student identifiers.

The engine sums **teacher-selected** points. Maximum is the sum of criterion
maxima. Percentage is points/maximum × 100, rounded half up to two decimals.
Any withheld criterion suppresses the whole-submission score.

Per-criterion override rates count overrides of available model suggestions,
including overrides retaining the same level. These describe workflow decisions,
not accuracy, fairness, expert agreement or measured learning outcomes. Missing
model suggestions are excluded from that rate's denominator.

## Commands and outputs

`prepare ASSESSMENT --out NEW_DIRECTORY` supports mutually exclusive `--model`
and `--fixture`. `--fixture` means scripted test-double responses, never live AI.
Model settings: `--endpoint`, `--allow-remote-model`, `--max-calls` (default 10,
maximum 20), `--timeout` (default/max 120 seconds). One attempt per answer, no
automatic retries. Extra answers after budget exhaustion remain blocked.

| Preparation | Final export |
| --- | --- |
| `pack.json` — sources, validated suggestions and digests | `results.json` — teacher-selected marks/feedback |
| `review-template.json` — pending decisions | `audit.json` — full private sources, model suggestions and decisions |
| `review.html` — source-first inert report | `feedback.html` — combined **private batch** feedback |
| `trace.json` — private raw model responses and usage | `scores.csv` — spreadsheet-protected text cells |

Consumed JSON and generated packs are <=2 MB. Use smaller batches for quote-heavy
outputs. Model context <=24 KB and response <=128 KB. Inputs must be UTF-8 regular
files; symlinks, pipes, duplicate fields, nonfinite values, lone Unicode surrogates
and excessive nesting are rejected. New output directories are required. Exit 0:
command completed; exit 2: invalid input/operational error; exit 3: review pack
created with blocked model rows. Exit 0 does not certify model correctness.

## Privacy and limits

All reports/traces can contain private student work. Opaque IDs do not anonymize
answer text. Files are not encrypted. **Do not publish a real batch or give its
combined feedback page to one student.** Distribute individual feedback through
your institution's approved process.

HTML escapes text and contains no scripts, network assets or forms. Formula-like
CSV text gets an apostrophe prefix; canonical JSON preserves teacher text. These
controls do not prove every spreadsheet application treats exports identically.

Finite output schemas reduce accepted actions, but do not solve prompt injection,
bias or automation bias. No student/model code is executed. Direct HTTP/TLS does
not follow redirects or use proxy settings. System DNS resolution remains outside
the post-resolution I/O deadline. The user-chosen endpoint is a trust boundary;
local HTTP can transmit a configured key to that local service.

Use a trusted local directory; concurrent hostile filesystem changes are outside
the security boundary. Output failures may leave incomplete files: use a fresh
directory and only consume successful commands. No telemetry, cloud account, LMS
writeback, OCR, PDF import or automatic pass/fail decision. No production-readiness,
general grading accuracy or complete-security claim.

## Architecture and development

- `core.py`: assessment validation, exact quote offsets and canonical digests.
- `provider.py` / `httpio.py`: real bounded model requests and failure handling.
- `review.py`: independent decisions, deterministic scores and moderation counts.
- `report.py`: escaped review/feedback and spreadsheet-protected exports.
- `files.py` / `cli.py`: bounded inputs and explicit workflow.

```bash
python -m pip install '.[dev]'
python -m unittest -v
python -m ruff check .
python -m ruff format --check .
python -m compileall -q rubrictrace scripts tests
python -m build --wheel
```

## Verification and license

Read [verification](docs/VERIFICATION.md) for actual local/CI/model evidence,
[validation](docs/VALIDATION.md) for research and alternatives,
[design](docs/DESIGN.md) for scope, [review](docs/REVIEW.md) for independent findings,
[security](SECURITY.md) and [contribution guide](CONTRIBUTING.md).

MIT, copyright Oshada Nilendra. HTTP transport and downloader adapted from his MIT
DataRescue release. Optional llama.cpp: MIT; official Qwen3-4B GGUF: Apache-2.0.
No model weights, competitor code, research text or student dataset is distributed.
