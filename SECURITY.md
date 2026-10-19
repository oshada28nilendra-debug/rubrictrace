# Security and privacy

This is a local formative-feedback moderation tool, not an authenticated grading
platform. Only run it in a trusted private directory. Do not publish student
answers, model traces, batch feedback or audit exports. Use aliases and comply
with your institution's approved data-handling process.

Model credentials are optional environment values. They are sent only to the
explicit user-chosen model endpoint and are not intentionally logged. Remote
models need explicit consent and HTTPS. Never include credentials in endpoint
URLs, examples, issues or commits. Treat provider responses as untrusted.

Validation rejects unsupported schemas, duplicate IDs/fields, invalid evidence,
stale review, pipes/symlinks, nonfinite numbers and Unicode surrogates. Outputs are
escaped; no model/student code runs. Exact evidence is not pedagogical proof.
Hashes are not signatures, authorization or proof of teacher attention.

Known boundaries: system DNS outside request deadline, user-selected endpoint,
unencrypted local files, concurrent malicious filesystem activity, provider data
retention, prompt injection/bias and diverse spreadsheet behavior. A clean secret
scan is not an absolute security guarantee.

Report a vulnerability through GitHub private vulnerability reporting if enabled.
If unavailable, ask the maintainer for a private channel without including secrets
or student records in a public issue. Rotate any actually exposed credential with
its provider; deleting a committed file does not remove public history.
