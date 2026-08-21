"""Neutral document node tree. Build Prompt v2 §3.4.

`html.py` and `docx.py` are thin adapters over this tree. Neither may hold
its own copy of document text (§19), so every string here arrives from the
clause repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar


class NodeKind(StrEnum):
    HEADING = "heading"
    PARA = "para"
    SUBPARA = "subpara"
    BULLET = "bullet"
    TABLE = "table"
    SIGNATURE = "signature"
    PAGE_BREAK = "page_break"
    LETTERHEAD = "letterhead"


@dataclass(frozen=True, slots=True)
class Node:
    """Base node.

    `kind` is a class-level property rather than a field. As a field it would
    force every subclass to give its own attributes defaults, since a
    defaulted base field cannot be followed by a non-defaulted one.
    """

    _KIND: ClassVar[NodeKind]

    @property
    def kind(self) -> NodeKind:
        return self._KIND


@dataclass(frozen=True, slots=True)
class Heading(Node):
    text: str
    level: int = 1
    clause_id: str = ""
    _KIND: ClassVar[NodeKind] = NodeKind.HEADING


@dataclass(frozen=True, slots=True)
class Para(Node):
    text: str
    clause_id: str = ""
    number: str = ""
    _KIND: ClassVar[NodeKind] = NodeKind.PARA


@dataclass(frozen=True, slots=True)
class SubPara(Node):
    text: str
    number: str = ""
    clause_id: str = ""
    _KIND: ClassVar[NodeKind] = NodeKind.SUBPARA


@dataclass(frozen=True, slots=True)
class Bullet(Node):
    text: str
    _KIND: ClassVar[NodeKind] = NodeKind.BULLET


@dataclass(frozen=True, slots=True)
class Table(Node):
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    clause_id: str = ""
    caption: str = ""
    _KIND: ClassVar[NodeKind] = NodeKind.TABLE

    def __post_init__(self) -> None:
        width = len(self.headers)
        for i, row in enumerate(self.rows):
            if len(row) != width:
                raise ValueError(f"table row {i} has {len(row)} cells, expected {width}")


@dataclass(frozen=True, slots=True)
class Signature(Node):
    lines: tuple[str, ...]
    _KIND: ClassVar[NodeKind] = NodeKind.SIGNATURE


@dataclass(frozen=True, slots=True)
class PageBreak(Node):
    _KIND: ClassVar[NodeKind] = NodeKind.PAGE_BREAK


@dataclass(frozen=True, slots=True)
class Letterhead(Node):
    lines: tuple[str, ...]
    _KIND: ClassVar[NodeKind] = NodeKind.LETTERHEAD


@dataclass(slots=True)
class Document:
    """A rendered document as a flat node sequence."""

    id: str
    title: str
    template_version: str = ""
    nodes: list[Node] = field(default_factory=list)

    def add(self, node: Node) -> None:
        self.nodes.append(node)

    def extend(self, nodes: list[Node]) -> None:
        self.nodes.extend(nodes)

    def text_nodes(self) -> list[str]:
        """Every visible string, for the pre-export placeholder scan (§18.4)."""
        out: list[str] = []
        for node in self.nodes:
            match node:
                case Heading(text=t) | Para(text=t) | SubPara(text=t) | Bullet(text=t):
                    out.append(t)
                case Table(headers=headers, rows=rows, caption=caption):
                    out.append(caption)
                    out.extend(headers)
                    for row in rows:
                        out.extend(row)
                case Signature(lines=lines) | Letterhead(lines=lines):
                    out.extend(lines)
                case _:
                    continue
        return [t for t in out if t]
