# Hermes PDF / form fill (local Minisforum + Jetson)

Why your current local LLM fails: Hermes's bundled `pdf` skill form flow needs many tool steps, vision crops, and coordinate math. `qwen3.5-4b-64k` is good for Home Assistant / chat tools, but it usually aborts or invents a fake PDF instead of writing AcroForm field values.

## What works on your stack

| Form type | Works with `qwen3.5-4b-64k`? | Approach |
|-----------|------------------------------|----------|
| Fillable AcroForm PDF | Yes (with this skill) | Scripts extract field IDs → model maps your data → script fills → Matrix attaches file |
| Flat / scanned PDF | No — switch model | `!model custom:gemma4:12b` + full `pdf` skill `forms.md` overlay path |

## Install on Jetson (Hermes host)

Copy this folder to the Jetson, then:

```bash
cd hermes-form-fill
chmod +x install-on-jetson.sh scripts/smoke_test.sh
./install-on-jetson.sh
# restart Hermes gateway / Docker so skills reload
```

Smoke test (optional, on any Linux with Python):

```bash
./scripts/smoke_test.sh
```

## How to use from FluffyChat

1. Keep daily model: `!model custom:qwen3.5-4b-64k`
2. Attach a **fillable** PDF in the Hermes DM
3. Prompt clearly:

```text
Use the simple-pdf-forms skill only.
1) check the attached PDF
2) list fields
3) fill with: full_name=Jane Doe, email=jane@example.com, agree=yes
4) dump to verify
5) reply with the absolute path to the filled PDF
```

Hermes should return a downloadable PDF attachment (deliverable mode picks up the path).

## Model notes (Minisforum 890M)

- Keep `qwen3.5-4b-64k` as Hermes default for reliability.
- You already have `gemma4:12b` (vision) — use it only for scanned/flat forms.
- Do not ask the 4B model to "draw" a filled form with reportlab; always use `form_cli.py fill`.

## Jetson deps

```bash
python3 -m pip install --user 'pypdf>=4.0'
# optional, for the full pdf skill / OCR path:
# sudo apt install -y poppler-utils qpdf
# python3 -m pip install --user pdfplumber reportlab pymupdf
```
