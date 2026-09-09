"""Generate a portable PDF from one completed Codex check run."""
import html
import io
import re

import fitz


VERDICT_COPY = {
    "PASS": ("Pass", "The output satisfies the checks supported by the available evidence."),
    "FAIL": ("Fail", "The output did not meet one or more checks."),
    "INDETERMINATE": ("Needs review", "The available evidence was not sufficient for a confident decision."),
}


def _text(value) -> str:
    cleaned = re.sub(r"(^|[\s(\"'`:=])(?:\.?[\\/])?(?:tasks?|workflows?)[\\/]", r"\1", str(value or ""), flags=re.I)
    cleaned = re.sub(r"(^|[\s(\"'`:=])(?:\.?[\\/])?tasks?[\\/]?(?=\s|[.,;:!?\"'`)]|$)", r"\1task folder", cleaned, flags=re.I)
    cleaned = re.sub(r"(^|[\s(\"'`:=])(?:\.?[\\/])?workflows?[\\/]?(?=\s|[.,;:!?\"'`)]|$)", r"\1workflow folder", cleaned, flags=re.I)
    return html.escape(cleaned)


def report_filename(run: dict, agent_name: str) -> str:
    task_name = (run.get("config_snapshot") or {}).get("task_name")
    stem = " - ".join(filter(None, (agent_name, task_name, "report")))
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", stem).strip(" .-")[:120]
    return f"{stem or 'task-check-report'}.pdf"


def build_check_report_pdf(run: dict, agent_name: str, include_config: bool = False) -> io.BytesIO:
    result = run.get("result_json") or {}
    snapshot = run.get("config_snapshot") or {}
    task_name = snapshot.get("task_name")
    verdict = str(run.get("final_verdict") or run.get("codex_verdict") or result.get("verdict") or "INDETERMINATE").upper()
    label, lede = VERDICT_COPY.get(verdict, VERDICT_COPY["INDETERMINATE"])
    standing = "Provisional" if run.get("review_status") == "PENDING" else "Final"
    checks = result.get("checks") if isinstance(result.get("checks"), list) else []
    rank = {"FAIL": 0, "INDETERMINATE": 1, "PASS": 2}
    checks = sorted(checks, key=lambda item: rank.get(str(item.get("status", "")).upper(), 1))

    provenance = " · ".join(filter(None, (agent_name, task_name)))
    if include_config and run.get("codex_model"):
        provenance += f" · {run['codex_model']} · {run.get('codex_reasoning_effort') or ''} reasoning"

    sections = []
    for check in checks:
        status = str(check.get("status") or "INDETERMINATE").upper()
        evidence = check.get("evidence") if isinstance(check.get("evidence"), list) else []
        citations = "".join(
            f'<li><strong>{_text(item.get("path"))}</strong><br>{_text(item.get("detail"))}</li>'
            for item in evidence if isinstance(item, dict)
        )
        sections.append(
            f'<section class="check check-{status.lower()}">'
            f'<h3><span>{_text(status)}</span> {_text(check.get("name") or "Unnamed check")}</h3>'
            f'<p class="reason">{_text(check.get("reason"))}</p>'
            f'<ul>{citations}</ul>'
            '</section>'
        )

    warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
    warning_html = ""
    if warnings:
        warning_html = '<section class="warnings"><h2>Warnings</h2><ul>' + "".join(
            f"<li>{_text(item)}</li>" for item in warnings
        ) + "</ul></section>"

    source = f"""
    <article>
      <header>
        <div class="standing">{_text(standing)}</div>
        <h1>{_text(label)}</h1>
        <p class="lede">{_text(lede)}</p>
        <p class="summary">{_text(result.get('summary') or run.get('result_summary'))}</p>
        <p class="provenance">{_text(provenance)}</p>
      </header>
      <h2>Validation checks</h2>
      {''.join(sections) if sections else '<p>No checks were returned.</p>'}
      {warning_html}
      <footer>Run {_text(run.get('id'))}</footer>
    </article>
    """
    css = """
      @page { size: A4; }
      body { font-family: sans-serif; color: #2a201f; font-size: 10pt; line-height: 1.45; }
      header { border-bottom: 1px solid #bcbcbc; padding-bottom: 16px; margin-bottom: 22px; }
      h1 { font-size: 30pt; margin: 3px 0 4px; color: #25477a; }
      h2 { font-size: 15pt; margin: 20px 0 10px; }
      h3 { font-size: 11pt; margin: 0 0 8px; }
      h3 span { font-size: 8pt; color: #25477a; margin-right: 8px; }
      p { margin: 0 0 9px; }
      .standing, .provenance, footer { color: #695f5e; font-size: 8.5pt; }
      .lede { font-size: 12pt; }
      .summary { font-weight: bold; }
      .check { border-top: 1px solid #dcdcdc; padding: 13px 0 9px; break-inside: avoid; }
      .check-fail h3 span { color: #a63129; }
      .check-pass h3 span { color: #1d6e42; }
      .check-indeterminate h3 span { color: #875d13; }
      .reason { max-width: 72ch; }
      ul { margin: 7px 0 0; padding-left: 18px; }
      li { margin-bottom: 7px; overflow-wrap: break-word; }
      li strong { color: #25477a; font-family: monospace; font-size: 8.5pt; }
      footer { border-top: 1px solid #dcdcdc; margin-top: 24px; padding-top: 8px; }
    """

    page = fitz.paper_rect("a4")
    content = fitz.Rect(48, 48, page.width - 48, page.height - 48)

    def page_rect(_number, _filled):
        return page, content, fitz.Identity

    document = fitz.Story(source, user_css=css).write_with_links(page_rect)
    document.set_metadata({"title": f"{agent_name} report", "subject": "Task Checker validation report"})
    output = io.BytesIO(document.tobytes(garbage=3, deflate=True))
    document.close()
    output.seek(0)
    return output
