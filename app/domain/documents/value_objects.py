"""Value objects for the documents context.

Value objects are immutable and compared by value.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Coordinates of a text span on a rendered page.

    Reserved for later phases: used to highlight the exact text on the original
    document as visual evidence of an answer. Normalized or absolute pixel units
    are agreed upon by the renderer.
    """

    x0: float
    y0: float
    x1: float
    y1: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    @classmethod
    def from_iterable(cls, values: tuple[float, float, float, float]) -> BoundingBox:
        x0, y0, x1, y1 = values
        return cls(x0=x0, y0=y0, x1=x1, y1=y1)
