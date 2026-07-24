#!/usr/bin/env python3
"""CLI for AcroForm PDF form check / list / fill / dump — small-model friendly."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.constants import FieldDictionaryAttributes
from pypdf.generic import DictionaryObject


def _monkeypatch_pypdf_opt() -> None:
    original_get_inherited = DictionaryObject.get_inherited

    def patched_get_inherited(self, key: str, default=None):
        result = original_get_inherited(self, key, default)
        if key == FieldDictionaryAttributes.Opt:
            if isinstance(result, list) and all(
                isinstance(v, list) and len(v) == 2 for v in result
            ):
                result = [r[0] for r in result]
        return result

    DictionaryObject.get_inherited = patched_get_inherited


def _full_annotation_field_id(annotation) -> str | None:
    components = []
    while annotation:
        field_name = annotation.get("/T")
        if field_name:
            components.append(field_name)
        annotation = annotation.get("/Parent")
    return ".".join(reversed(components)) if components else None


def _make_field_dict(field, field_id: str) -> dict:
    field_dict: dict = {"field_id": field_id}
    ft = field.get("/FT")
    if ft == "/Tx":
        field_dict["type"] = "text"
    elif ft == "/Btn":
        field_dict["type"] = "checkbox"
        states = field.get("/_States_", [])
        if len(states) == 2:
            if "/Off" in states:
                field_dict["checked_value"] = (
                    states[0] if states[0] != "/Off" else states[1]
                )
                field_dict["unchecked_value"] = "/Off"
            else:
                field_dict["checked_value"] = states[0]
                field_dict["unchecked_value"] = states[1]
        else:
            field_dict["checked_value"] = "/Yes"
            field_dict["unchecked_value"] = "/Off"
    elif ft == "/Ch":
        field_dict["type"] = "choice"
        states = field.get("/_States_", [])
        field_dict["choice_options"] = [
            {"value": state[0], "text": state[1]} for state in states
        ]
    else:
        field_dict["type"] = f"unknown ({ft})"
    return field_dict


def get_field_info(reader: PdfReader) -> list[dict]:
    fields = reader.get_fields() or {}
    field_info_by_id: dict[str, dict] = {}
    possible_radio_names: set[str] = set()

    for field_id, field in fields.items():
        if field.get("/Kids"):
            if field.get("/FT") == "/Btn":
                possible_radio_names.add(field_id)
            continue
        field_info_by_id[field_id] = _make_field_dict(field, field_id)

    radio_fields_by_id: dict[str, dict] = {}
    for page_index, page in enumerate(reader.pages):
        annotations = page.get("/Annots", []) or []
        for ann in annotations:
            field_id = _full_annotation_field_id(ann)
            if field_id in field_info_by_id:
                field_info_by_id[field_id]["page"] = page_index + 1
                field_info_by_id[field_id]["rect"] = ann.get("/Rect")
            elif field_id in possible_radio_names:
                try:
                    on_values = [v for v in ann["/AP"]["/N"] if v != "/Off"]
                except KeyError:
                    continue
                if len(on_values) == 1:
                    rect = ann.get("/Rect")
                    if field_id not in radio_fields_by_id:
                        radio_fields_by_id[field_id] = {
                            "field_id": field_id,
                            "type": "radio_group",
                            "page": page_index + 1,
                            "radio_options": [],
                        }
                    radio_fields_by_id[field_id]["radio_options"].append(
                        {"value": on_values[0], "rect": rect}
                    )

    fields_with_location = []
    for field_info in field_info_by_id.values():
        if "page" in field_info:
            fields_with_location.append(field_info)

    def sort_key(f):
        if "radio_options" in f:
            rect = f["radio_options"][0]["rect"] or [0, 0, 0, 0]
        else:
            rect = f.get("rect") or [0, 0, 0, 0]
        return [f.get("page"), -rect[1], rect[0]]

    sorted_fields = fields_with_location + list(radio_fields_by_id.values())
    sorted_fields.sort(key=sort_key)
    return sorted_fields


def cmd_check(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if fields:
        print("FILLABLE: yes")
        print(f"FIELD_COUNT: {len(fields)}")
        return 0
    print("FILLABLE: no")
    print("FIELD_COUNT: 0")
    return 0


def cmd_list(pdf_path: str, out_json: str) -> int:
    reader = PdfReader(pdf_path)
    if not reader.get_fields():
        print("ERROR: PDF has no fillable AcroForm fields", file=sys.stderr)
        return 1
    info = get_field_info(reader)
    Path(out_json).write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"Wrote {len(info)} fields to {out_json}")
    # Compact summary for small models
    for f in info:
        extra = ""
        if f.get("type") == "checkbox":
            extra = f" checked={f.get('checked_value')} unchecked={f.get('unchecked_value')}"
        elif f.get("type") == "radio_group":
            vals = [o["value"] for o in f.get("radio_options", [])]
            extra = f" options={vals}"
        elif f.get("type") == "choice":
            vals = [o["value"] for o in f.get("choice_options", [])]
            extra = f" options={vals}"
        print(f"- {f['field_id']} | page={f.get('page')} | type={f.get('type')}{extra}")
    return 0


def _validation_error(field_info: dict, field_value) -> str | None:
    field_type = field_info["type"]
    field_id = field_info["field_id"]
    if field_type == "checkbox":
        checked_val = field_info.get("checked_value")
        unchecked_val = field_info.get("unchecked_value")
        if field_value != checked_val and field_value != unchecked_val:
            return (
                f'ERROR: Invalid value "{field_value}" for checkbox "{field_id}". '
                f'Use "{checked_val}" or "{unchecked_val}"'
            )
    elif field_type == "radio_group":
        option_values = [opt["value"] for opt in field_info.get("radio_options", [])]
        if field_value not in option_values:
            return (
                f'ERROR: Invalid value "{field_value}" for radio "{field_id}". '
                f"Valid: {option_values}"
            )
    elif field_type == "choice":
        choice_values = [opt["value"] for opt in field_info.get("choice_options", [])]
        if field_value not in choice_values:
            return (
                f'ERROR: Invalid value "{field_value}" for choice "{field_id}". '
                f"Valid: {choice_values}"
            )
    return None


def cmd_fill(pdf_path: str, values_json: str, output_pdf: str) -> int:
    _monkeypatch_pypdf_opt()
    fields = json.loads(Path(values_json).read_text(encoding="utf-8"))
    if not isinstance(fields, list):
        print("ERROR: field_values.json must be a JSON array", file=sys.stderr)
        return 1

    reader = PdfReader(pdf_path)
    field_info = get_field_info(reader)
    by_id = {f["field_id"]: f for f in field_info}

    has_error = False
    fields_by_page: dict[int, dict] = {}
    for field in fields:
        if "value" not in field:
            continue
        field_id = field["field_id"]
        page = field.get("page")
        existing = by_id.get(field_id)
        if not existing:
            print(f"ERROR: `{field_id}` is not a valid field ID")
            has_error = True
            continue
        if page != existing.get("page"):
            print(
                f"ERROR: Incorrect page for `{field_id}` "
                f"(got {page}, expected {existing.get('page')})"
            )
            has_error = True
            continue
        err = _validation_error(existing, field["value"])
        if err:
            print(err)
            has_error = True
            continue
        fields_by_page.setdefault(page, {})[field_id] = field["value"]

    if has_error:
        return 1
    if not fields_by_page:
        print("ERROR: no field values to apply", file=sys.stderr)
        return 1

    writer = PdfWriter(clone_from=reader)
    for page, field_values in fields_by_page.items():
        writer.update_page_form_field_values(
            writer.pages[page - 1], field_values, auto_regenerate=False
        )
    writer.set_need_appearances_writer(True)

    out = Path(output_pdf)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    print(f"FILLED_OK: {out.resolve()}")
    print(f"FIELDS_WRITTEN: {sum(len(v) for v in fields_by_page.values())}")
    return 0


def cmd_dump(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        print("FILLABLE: no")
        return 0
    print("FILLABLE: yes")
    for name, field in fields.items():
        value = field.get("/V")
        if value is not None:
            value = str(value)
        print(f"{name}={value!r}")
    return 0


def usage() -> None:
    print(
        """Usage:
  form_cli.py check <input.pdf>
  form_cli.py list  <input.pdf> <field_info.json>
  form_cli.py fill  <input.pdf> <field_values.json> <output.pdf>
  form_cli.py dump  <input.pdf>
""",
        file=sys.stderr,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        usage()
        return 2
    cmd = argv[1]
    try:
        if cmd == "check" and len(argv) == 3:
            return cmd_check(argv[2])
        if cmd == "list" and len(argv) == 4:
            return cmd_list(argv[2], argv[3])
        if cmd == "fill" and len(argv) == 5:
            return cmd_fill(argv[2], argv[3], argv[4])
        if cmd == "dump" and len(argv) == 3:
            return cmd_dump(argv[2])
    except FileNotFoundError as e:
        print(f"ERROR: file not found: {e.filename}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
