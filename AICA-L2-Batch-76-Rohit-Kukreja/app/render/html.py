"""HTML adapter over the node tree. Build Prompt v2 §3.4.

A thin adapter: it decides markup, never wording. Every visible string
arrives from `content/` via the node tree, which is why no literal here is
longer than a tag name. `tests/test_no_hardcoded_text.py` enforces that.
"""

from __future__ import annotations

from html import escape

from app.render.base import (
    Bullet,
    Document,
    Heading,
    Letterhead,
    Node,
    PageBreak,
    Para,
    Signature,
    SubPara,
    Table,
)

# §13 — Jinja2 autoescaping is on and `| safe` is never used on user data.
# This module is the reason that holds: it emits already-escaped markup, so
# the template inserts one trusted string rather than assembling HTML from
# untrusted values itself.


def _esc(text: str) -> str:
    return escape(text, quote=True)


def _attr(name: str, value: str) -> str:
    return f' {name}="{_esc(value)}"' if value else ""


def render_node(node: Node) -> str:
    match node:
        case Heading(text=text, level=level):
            tag = f"h{min(max(level, 1), 6)}"
            return f'<{tag} class="doc-heading">{_esc(text)}</{tag}>'

        case Para(text=text, clause_id=clause_id, number=number):
            # The space sits OUTSIDE the span deliberately. `.clause-no` is an
            # inline-block, and a trailing space inside one is trimmed — the
            # number would look separated but copy out as "(a)The Company…".
            marker = f'<span class="clause-no">{_esc(number)}</span> ' if number else ""
            return (
                f'<p class="doc-para"{_attr("data-clause", clause_id)}>' f"{marker}{_esc(text)}</p>"
            )

        case SubPara(text=text, number=number, clause_id=clause_id):
            # The space sits OUTSIDE the span deliberately. `.clause-no` is an
            # inline-block, and a trailing space inside one is trimmed — the
            # number would look separated but copy out as "(a)The Company…".
            marker = f'<span class="clause-no">{_esc(number)}</span> ' if number else ""
            return (
                f'<p class="doc-subpara"{_attr("data-clause", clause_id)}>'
                f"{marker}{_esc(text)}</p>"
            )

        case Bullet(text=text):
            return f'<li class="doc-bullet">{_esc(text)}</li>'

        case Table(headers=headers, rows=rows, caption=caption, clause_id=clause_id):
            return _render_table(headers, rows, caption, clause_id)

        case Signature(lines=lines):
            body = "".join(f"<div>{_esc(line)}</div>" for line in lines)
            return f'<div class="doc-signature">{body}</div>'

        case PageBreak():
            return '<div class="doc-page-break"></div>'

        case Letterhead(lines=lines):
            body = "".join(f"<div>{_esc(line)}</div>" for line in lines)
            return f'<header class="doc-letterhead">{body}</header>'

        case _:  # pragma: no cover - every NodeKind is handled above
            raise TypeError(f"no HTML adapter for {type(node).__name__}")


def _render_table(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    caption: str,
    clause_id: str,
) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    caption_html = f"<caption>{_esc(caption)}</caption>" if caption else ""
    return (
        f'<table class="doc-table"{_attr("data-clause", clause_id)}>'
        f"{caption_html}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def render(document: Document) -> str:
    """The document surface. Print CSS prints this element and nothing else."""
    parts: list[str] = []
    open_list = False

    for node in document.nodes:
        is_bullet = isinstance(node, Bullet)
        if is_bullet and not open_list:
            parts.append('<ul class="doc-list">')
            open_list = True
        elif not is_bullet and open_list:
            parts.append("</ul>")
            open_list = False
        parts.append(render_node(node))

    if open_list:
        parts.append("</ul>")

    # The template version is not printed inside the document either (19 Aug
    # 2026). The preview exists to show what will be signed, and a version
    # marker on the page would be the one thing on it that the .docx no longer
    # carries. It is still shown in the page CHROME above the document, where it
    # is information about the file rather than part of it.
    return (
        f'<article class="document-surface"{_attr("data-document", document.id)}>'
        f'{"".join(parts)}</article>'
    )
