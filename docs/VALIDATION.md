# Validation — researched 19 October 2026

**Decision: proceed with a narrow formative moderation tool.** This is a product
hypothesis; no teacher interviews, adoption measures or market-size claims.

- **Target/pain:** teachers/teaching assistants need to inspect AI feedback against
  the actual answer and an explicit rubric before accepting a mark.
- **Evidence:** Mathew et al., *LLMs Do Not Grade Essays Like Humans*, submitted
  24 March 2026, reports weak/variable human agreement in its evaluated GPT/Llama
  essay-scoring setup. This motivates moderation, not a general result for all
  models, subjects or short answers. https://arxiv.org/abs/2603.23714
- **Alternative 1:** Gradescope offers rubrics, instructor review, answer grouping,
  exports and regrades; its guide describes AI grouping for some fixed-template
  question types. We do not claim it lacks human control.
  https://www.gradescope.com/get_started
- **Alternative 2:** Moodle rubrics provide criterion/level selections, remarks and
  deterministic score calculation. This is a strong manual baseline; RubricTrace
  is not an LMS replacement. https://docs.moodle.org/en/Rubrics
- **Alternative 3:** EssayGrader advertises custom-rubric AI feedback and LMS
  integration. Marketing accuracy/speed is not independent measured evidence.
  https://www.essaygrader.ai/
- **Gap/differentiator hypothesis:** small forkable local review packs combining
  exact student quote offsets, finite level IDs, explicit abstention, digest-bound
  moderation and independent score recomputation. No claim of global novelty or
  that competitors lack these capabilities.
- **Feasibility:** bounded stdlib CLI + inert HTML/JSON, real compatible-model
  adapter, authored fixtures and deterministic teacher-selected score arithmetic.
- **Risks:** exact quotes can be irrelevant; subjective descriptors, bias,
  automation bias, prompt injection and privacy remain. Teacher confirmation and
  hashes are not authentication or proof of attention. No high-stakes automation.

Inventory inspected: prior software-debugging, evidence-audit, data profiling and
CSV-cleaning releases do not implement this educational moderation workflow.
Reuse: bounded HTTP transport and optional downloader adapted from Oshada Nilendra's
MIT DataRescue, copyright retained in LICENSE. Python runtime dependencies: none.
Optional llama.cpp MIT; official Qwen3-1.7B GGUF Apache-2.0:
https://huggingface.co/Qwen/Qwen3-1.7B-GGUF . No weights or student dataset bundled.
