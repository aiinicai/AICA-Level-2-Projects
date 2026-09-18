"""Signature / stamp placement templates.

A template captures everything needed to reproduce a placement: which image,
how big, where on the page (as *percentages* of page width/height so it is
correct regardless of A4/Letter/Legal/landscape/scanned page size), and which
pages to apply it to.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from models.enums import PositionPreset, SignatureKind


@dataclass
class SignatureTemplate:
    """A reusable, named signature/stamp configuration.

    Position/size are stored as percentages of the page's width/height
    (0-100) so the same template produces a proportionally identical result
    on A4, Letter, Legal, portrait or landscape pages. ``PositionPreset``
    values (other than CUSTOM) are resolved to concrete percentages at
    render time based on ``margin_mm`` and the actual page size -- see
    :mod:`core.signature_engine`.
    """

    name: str = "Untitled Template"
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: SignatureKind = SignatureKind.SIGNATURE
    image_path: str = ""

    position_preset: PositionPreset = PositionPreset.BOTTOM_RIGHT
    # Only used when position_preset == CUSTOM (percentages of page size, 0-100)
    custom_x_pct: float = 70.0
    custom_y_pct: float = 85.0

    width_pct: float = 20.0  # width as % of page width
    height_pct: float = 8.0  # height as % of page height
    maintain_aspect_ratio: bool = True

    margin_mm: float = 10.0
    opacity: float = 100.0  # 0-100
    rotation_degrees: float = 0.0

    page_rule_expression: str = "last"  # see core.page_selection

    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "template_id": self.template_id,
            "kind": self.kind.value,
            "image_path": self.image_path,
            "position_preset": self.position_preset.value,
            "custom_x_pct": self.custom_x_pct,
            "custom_y_pct": self.custom_y_pct,
            "width_pct": self.width_pct,
            "height_pct": self.height_pct,
            "maintain_aspect_ratio": self.maintain_aspect_ratio,
            "margin_mm": self.margin_mm,
            "opacity": self.opacity,
            "rotation_degrees": self.rotation_degrees,
            "page_rule_expression": self.page_rule_expression,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: dict) -> "SignatureTemplate":
        return SignatureTemplate(
            name=data.get("name", "Untitled Template"),
            template_id=data.get("template_id", uuid.uuid4().hex),
            kind=SignatureKind(data.get("kind", SignatureKind.SIGNATURE.value)),
            image_path=data.get("image_path", ""),
            position_preset=PositionPreset(data.get("position_preset", PositionPreset.BOTTOM_RIGHT.value)),
            custom_x_pct=float(data.get("custom_x_pct", 70.0)),
            custom_y_pct=float(data.get("custom_y_pct", 85.0)),
            width_pct=float(data.get("width_pct", 20.0)),
            height_pct=float(data.get("height_pct", 8.0)),
            maintain_aspect_ratio=bool(data.get("maintain_aspect_ratio", True)),
            margin_mm=float(data.get("margin_mm", 10.0)),
            opacity=float(data.get("opacity", 100.0)),
            rotation_degrees=float(data.get("rotation_degrees", 0.0)),
            page_rule_expression=data.get("page_rule_expression", "last"),
            description=data.get("description", ""),
        )
