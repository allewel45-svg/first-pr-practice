#!/usr/bin/env bash
# Local smoke test: create sample form, list fields, fill, dump.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -q 'pypdf>=4.0' reportlab
python3 scripts/make_sample_form.py
python3 scripts/form_cli.py check scripts/sample_fillable.pdf
python3 scripts/form_cli.py list scripts/sample_fillable.pdf /tmp/field_info.json

python3 - <<'PY'
import json
from pathlib import Path
info = json.loads(Path("/tmp/field_info.json").read_text())
values = []
for f in info:
    fid = f["field_id"]
    page = f["page"]
    if f["type"] == "text" and "name" in fid.lower():
        values.append({"field_id": fid, "page": page, "value": "Jane Doe"})
    elif f["type"] == "text" and "email" in fid.lower():
        values.append({"field_id": fid, "page": page, "value": "jane@example.com"})
    elif f["type"] == "checkbox":
        values.append({"field_id": fid, "page": page, "value": f["checked_value"]})
Path("/tmp/field_values.json").write_text(json.dumps(values, indent=2))
print(json.dumps(values, indent=2))
PY

python3 scripts/form_cli.py fill scripts/sample_fillable.pdf /tmp/field_values.json /tmp/filled_sample.pdf
python3 scripts/form_cli.py dump /tmp/filled_sample.pdf
echo "SMOKE_OK"
