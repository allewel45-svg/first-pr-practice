---
name: simple-pdf-forms
description: "Fill and read AcroForm PDF forms with a small local LLM. Prefer this over the full pdf skill forms.md flow when using models under ~14B."
version: 1.0.0
author: Al Lewel / Hermes local setup
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Forms, AcroForm, Documents, Productivity]
    related_skills: [pdf, ocr-and-documents]
---

# Simple PDF Forms (local / small-model path)

Use this skill whenever the user wants to **read or fill a PDF form** and you are running on a **local model (4B–14B)**.

Do **not** invent a filled PDF by writing reportlab pages that look like the form.
Do **not** follow the full visual/zoom `forms.md` workflow unless this skill fails (non-fillable / scanned PDF).

Scripts live in this skill's `scripts/` directory. Run them from there, or with absolute paths.

## Goal

Produce a real filled PDF file on disk, then mention its absolute path in your reply so the Matrix/FluffyChat gateway can attach it.

## Procedure (always in this order)

### 1. Locate the input PDF

- Matrix/FluffyChat attachments are downloaded for you — use the local path Hermes provides.
- If the user gave a path, verify it exists with the terminal tool.

### 2. Check whether it is fillable

```bash
python3 scripts/form_cli.py check "/path/to/input.pdf"
```

- If it prints `FILLABLE: yes` → continue with this skill.
- If `FILLABLE: no` → tell the user this is a flat/scanned form. Options:
  1. Ask them for a fillable (AcroForm) PDF, or
  2. Switch model to a vision-capable mid-size model (`gemma4:12b`) and use the bundled `pdf` skill `forms.md` non-fillable path.
  Do not attempt coordinate overlay with a 4B text model.

### 3. List every field

```bash
python3 scripts/form_cli.py list "/path/to/input.pdf" "/tmp/field_info.json"
```

Read `/tmp/field_info.json`. Each entry has `field_id`, `page`, `type`, and for checkboxes/radios/choices the allowed values.

### 4. Map the user's data → values JSON

Create `/tmp/field_values.json` as a JSON **array**:

```json
[
  {
    "field_id": "exact_id_from_field_info",
    "page": 1,
    "value": "Jane Doe"
  },
  {
    "field_id": "AgreeCheckbox",
    "page": 1,
    "value": "/Yes"
  }
]
```

Rules:
- `field_id` and `page` must match `field_info.json` exactly.
- For checkboxes use `checked_value` / `unchecked_value` from field info (often `/Yes` and `/Off`).
- For radio/choice use one of the listed option values only.
- Skip fields you do not have data for — do not invent personal data.
- If the user attached a source document (ID, resume, etc.), extract facts from that first, then map.

### 5. Fill and write the output PDF

```bash
python3 scripts/form_cli.py fill \
  "/path/to/input.pdf" \
  "/tmp/field_values.json" \
  "/tmp/filled_form.pdf"
```

If the script prints `ERROR:` lines, fix `field_values.json` and re-run. Do not hand-edit the PDF.

### 6. Verify

```bash
python3 scripts/form_cli.py dump "/tmp/filled_form.pdf"
```

Confirm the values you set appear. Then reply with a short summary **and the absolute path** `/tmp/filled_form.pdf` so the gateway can upload it.

## Reading a filled form

```bash
python3 scripts/form_cli.py dump "/path/to/any.pdf"
```

Returns field id → current value. Use this when the user asks what is already filled in.

## Pitfalls

- Wrong skill path: always run `scripts/form_cli.py` from this skill directory (or pass absolute script paths).
- Partial fills are OK — better than inventing SSN/address/etc.
- XFA-only PDFs may show as non-fillable; tell the user AcroForm is required for this path.
- Do not enable the full 50-tool Hermes toolset for form tasks — terminal + file tools are enough.

## When to escalate

Escalate to the full `pdf` skill + vision model when:
- `FILLABLE: no`
- User needs handwritten/scanned form overlay
- Field IDs are opaque and you cannot map labels without seeing the page layout
