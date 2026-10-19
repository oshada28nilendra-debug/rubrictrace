"""Escaped inert reports; no scripts, external assets, server or LMS writes."""

import csv
import html
import json
from pathlib import Path
from .core import Error, validate_pack


def esc(value):
    return html.escape(str(value), quote=True)


def document(title, body):
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">'
        f"<title>{esc(title)}</title><style>body{{font:17px/1.6 system-ui;color:#242820;background:#f6f4ed;max-width:1050px;margin:3rem auto;padding:0 1.5rem}}"
        "article,section{background:#fffefa;border:1px solid #d4d8cb;padding:1.5rem;margin:1rem 0;border-radius:12px}pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}"
        "h1,h2,h3{line-height:1.2}.meta{color:#59634e;font-size:.9rem}code{overflow-wrap:anywhere}</style><body>"
        + body
        + "</body></html>"
    )


def render_pack(pack):
    validate_pack(pack)
    a = pack["assessment"]
    parts = [
        f'<p class="meta">RUBRICTRACE · {esc(pack["mode"])} mode</p><h1>{esc(a["title"])}</h1>',
        "<p><strong>No final score.</strong> Read each answer before the AI suggestion. Exact quotations prove location, not correct assessment.</p>",
        "<p>Edit review-template.json: choose accept, override with a note, or withhold. Add your own student feedback, reviewer alias and explicit confirmation. Run export to recompute scores.</p>",
        f"<section><h2>Assignment prompt</h2><pre>{esc(a['prompt'])}</pre></section>",
    ]
    for s in a["submissions"]:
        parts.append(
            f"<article><h2>{esc(s['id'])}</h2><h3>Student response</h3><pre>{esc(s['text'] or '[Blank answer]')}</pre>"
        )
        for c in a["rubric"]:
            row = next(
                r
                for r in pack["suggestions"]
                if r["submission_id"] == s["id"] and r["criterion_id"] == c["id"]
            )
            parts.append(f"<section><h3>{esc(c['id'])} — {esc(c['description'])}</h3><ul>")
            for level in c["levels"]:
                parts.append(
                    f"<li>{esc(level['id'])} ({level['points']} points): {esc(level['description'])}</li>"
                )
            parts.append(
                f"</ul><h3>AI suggestion</h3><p>{esc(row['status'])}: {esc(row['level'])}</p><blockquote>{esc(row['quote'])}</blockquote><p>{esc(row['reason'])}</p>"
            )
            if row["span"]:
                parts.append(
                    f'<p class="meta">Unicode character offsets [{row["span"]["start"]}, {row["span"]["end"]}); first exact match.</p>'
                )
            parts.append("</section>")
        parts.append("</article>")
    parts.append(
        f'<p class="meta">Private review material. Pack digest: <code>{esc(pack["digest"])}</code></p>'
    )
    return document(a["title"], "".join(parts))


def create_output(path):
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=False, mode=0o700)
    except OSError:
        raise Error("Output directory must be new and writable") from None
    return path


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def spreadsheet(value):
    value = str(value)
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))
        else value
    )


def write_results(result, output):
    out = create_output(output)
    write_json(out / "results.json", {k: v for k, v in result.items() if k != "audit"})
    write_json(out / "audit.json", result)
    parts = [
        f"<h1>{esc(result['title'])}</h1><p>Teacher-reviewed formative feedback. Keep this combined class report private.</p>"
    ]
    with (out / "scores.csv").open("x", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["submission_id", "status", "points", "maximum", "percentage", "feedback"])
        for s in result["results"]:
            feedback = "\n".join(r["feedback"] for r in s["criteria"])
            writer.writerow(
                [
                    spreadsheet(s["submission_id"]),
                    s["status"],
                    s["points"],
                    s["maximum"],
                    s["percentage"],
                    spreadsheet(feedback),
                ]
            )
            parts.append(
                f"<article><h2>{esc(s['submission_id'])}</h2><p>{esc(s['status'])} · {esc(s['points'])} / {s['maximum']} · {esc(s['percentage'])}%</p>"
            )
            for r in s["criteria"]:
                parts.append(f"<h3>{esc(r['criterion_id'])}</h3><pre>{esc(r['feedback'])}</pre>")
            parts.append("</article>")
    (out / "feedback.html").write_text(document(result["title"], "".join(parts)), encoding="utf-8")
