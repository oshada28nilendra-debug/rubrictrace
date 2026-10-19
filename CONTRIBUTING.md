# Contributing

Install `python -m pip install '.[dev]'`, run `python -m unittest -v`, Ruff checks,
compile and wheel build as shown in README. Use a feature branch and pull request;
keep model integration, deterministic rules, review and rendering separate.

Use authored fictional submissions. Never add real student data, keys, runtime
binaries or model weights. A model test double must be labelled; ordinary HTTP
tests do not establish real inference. Add a failing regression for material
correctness fixes. Preserve failed live attempts rather than replacing history.

New scoring rules need explicit schemas, predictable arithmetic and teacher review.
No autonomous high-stakes grading, external publication or paid calls by default.
Discuss major schema changes before implementation; hashes and schema versions
bind reviews to exact content. No automatic merge.
