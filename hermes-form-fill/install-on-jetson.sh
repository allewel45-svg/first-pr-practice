#!/usr/bin/env bash
# Install simple-pdf-forms skill + deps on the Jetson (Hermes host).
set -euo pipefail

SKILL_NAME="simple-pdf-forms"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DEST="${HERMES_HOME}/skills/${SKILL_NAME}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Installing Python deps (pypdf)"
python3 -m pip install --user -q 'pypdf>=4.0'

echo "==> Installing skill to ${DEST}"
mkdir -p "${DEST}/scripts"
cp "${ROOT}/skill/SKILL.md" "${DEST}/SKILL.md"
cp "${ROOT}/scripts/form_cli.py" "${DEST}/scripts/form_cli.py"
chmod +x "${DEST}/scripts/form_cli.py"

# Also drop a copy next to bundled pdf skill if present (optional convenience)
BUNDLED_PDF="$(find "${HERMES_HOME}" /opt /home -path '*/skills/productivity/pdf' -type d 2>/dev/null | head -1 || true)"
if [[ -n "${BUNDLED_PDF}" ]]; then
  echo "==> Found bundled pdf skill at ${BUNDLED_PDF}"
fi

echo "==> Smoke test"
python3 "${DEST}/scripts/form_cli.py" || true

cat <<EOF

Installed: ${DEST}

Next steps on Jetson:
  1. Restart Hermes gateway / Docker container so it reloads skills.
  2. In FluffyChat DM @hermes:
       !model custom:qwen3.5-4b-64k
     (keep this for fillable AcroForms)

  3. For scanned / flat forms only, temporarily switch:
       !model custom:gemma4:12b
     and ask Hermes to use the full pdf skill forms.md path.

  4. Test prompt:
       "Use the simple-pdf-forms skill. Check then fill this PDF with:
        name=Jane Doe, email=jane@example.com
        Return the filled PDF."

EOF
