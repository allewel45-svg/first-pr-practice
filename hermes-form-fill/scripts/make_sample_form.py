#!/usr/bin/env python3
"""Generate a tiny AcroForm PDF for end-to-end smoke tests (reportlab)."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def build(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 14)
    c.drawString(72, 740, "Sample fillable form")
    c.setFont("Helvetica", 11)
    c.drawString(72, 705, "Full name:")
    c.acroForm.textfield(
        name="full_name",
        tooltip="Full name",
        x=150,
        y=690,
        width=300,
        height=20,
        borderWidth=1,
        borderColor=None,
        fillColor=None,
        textColor=None,
        forceBorder=True,
    )
    c.drawString(72, 665, "Email:")
    c.acroForm.textfield(
        name="email",
        tooltip="Email",
        x=150,
        y=650,
        width=300,
        height=20,
        borderWidth=1,
        borderColor=None,
        fillColor=None,
        textColor=None,
        forceBorder=True,
    )
    c.drawString(72, 620, "Agree:")
    c.acroForm.checkbox(
        name="agree",
        tooltip="Agree",
        x=150,
        y=610,
        size=14,
        checked=False,
        buttonStyle="check",
    )
    c.save()
    print(f"Wrote {path}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_fillable.pdf"
    build(out)
