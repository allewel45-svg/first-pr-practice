#!/usr/bin/env bash
# Remove local Ollama from the Jetson so Hermes only uses Minisforum via SSH tunnel.
# Run on Jetson as: lew
#   chmod +x remove-local-ollama.sh && ./remove-local-ollama.sh
set -euo pipefail

echo "=== 1) Stop / disable / mask local Ollama service ==="
sudo systemctl stop ollama 2>/dev/null || true
sudo systemctl disable ollama 2>/dev/null || true
sudo systemctl mask ollama 2>/dev/null || true
sudo rm -f /etc/systemd/system/ollama.service
sudo rm -rf /etc/systemd/system/ollama.service.d
sudo systemctl daemon-reload

echo "=== 2) Remove binary, data, user ==="
# Official Linux install locations
sudo rm -f /usr/local/bin/ollama /usr/bin/ollama
sudo rm -rf /usr/share/ollama /usr/lib/ollama
rm -rf "${HOME}/.ollama"
sudo userdel -r ollama 2>/dev/null || true
sudo groupdel ollama 2>/dev/null || true

echo "=== 3) Docker leftovers (if any) ==="
if command -v docker >/dev/null 2>&1; then
  docker ps -a --filter name=ollama --format '{{.ID}} {{.Names}}' || true
  mapfile -t OLLAMA_CTRS < <(docker ps -aq --filter name=ollama 2>/dev/null || true)
  if ((${#OLLAMA_CTRS[@]})); then
    docker rm -f "${OLLAMA_CTRS[@]}" || true
  fi
  mapfile -t OLLAMA_IMGS < <(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' 2>/dev/null | awk 'tolower($0) ~ /ollama/ {print $2}' || true)
  if ((${#OLLAMA_IMGS[@]})); then
    docker rmi -f "${OLLAMA_IMGS[@]}" || true
  fi
else
  echo "(docker not installed — skip)"
fi

echo "=== 4) Kill any stray ollama processes ==="
if pgrep -x ollama >/dev/null 2>&1; then
  sudo pkill -x ollama || true
  sleep 1
fi

echo "=== 5) Point Hermes at Minisforum tunnel (127.0.0.1:11434) ==="
if command -v hermes >/dev/null 2>&1; then
  hermes config set model.provider custom || true
  hermes config set model.base_url http://127.0.0.1:11434/v1 || true
  hermes config set model.context_length 64000 || true
  # Keep current default if already set; otherwise set the known Minisforum model
  CURRENT_DEFAULT="$(hermes config get model.default 2>/dev/null || true)"
  if [[ -z "${CURRENT_DEFAULT}" || "${CURRENT_DEFAULT}" == *null* || "${CURRENT_DEFAULT}" == *anthropic* || "${CURRENT_DEFAULT}" == *openrouter* || "${CURRENT_DEFAULT}" == *claude* ]]; then
    hermes config set model.default qwen3.5-4b-64k || true
  fi
  echo "--- Hermes model config ---"
  hermes config get model.provider || true
  hermes config get model.base_url || true
  hermes config get model.default || true
else
  echo "WARN: hermes CLI not found on PATH — edit ~/.hermes/config.yaml manually:"
  echo "  model.provider: custom"
  echo "  model.base_url: http://127.0.0.1:11434/v1"
  echo "  model.default: qwen3.5-4b-64k"
fi

# Also scrub .env leftovers that might prefer cloud APIs
ENV_FILE="${HOME}/.hermes/.env"
if [[ -f "${ENV_FILE}" ]]; then
  if grep -qE '^(LLM_MODEL|OPENROUTER_API_KEY|ANTHROPIC_API_KEY)=' "${ENV_FILE}"; then
    echo "=== Commenting cloud LLM keys/models in ${ENV_FILE} ==="
    cp -a "${ENV_FILE}" "${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
    sed -i -E 's/^(LLM_MODEL=)/# \1/; s/^(OPENROUTER_API_KEY=)/# \1/; s/^(ANTHROPIC_API_KEY=)/# \1/' "${ENV_FILE}"
  fi
fi

echo
echo "=== VERIFY (local Ollama must be gone) ==="
if command -v ollama >/dev/null 2>&1; then
  echo "FAIL: ollama binary still on PATH: $(command -v ollama)"
else
  echo "OK: no ollama binary"
fi
for p in /usr/local/bin/ollama /usr/bin/ollama /usr/share/ollama "${HOME}/.ollama"; do
  if [[ -e "${p}" ]]; then
    echo "FAIL: still exists: ${p}"
  else
    echo "OK: absent ${p}"
  fi
done
getent passwd ollama >/dev/null 2>&1 && echo "FAIL: ollama user still exists" || echo "OK: no ollama user"
pgrep -af '[o]llama' && echo "FAIL: ollama process running" || echo "OK: no ollama process"

echo
echo "=== VERIFY (Minisforum tunnel must be the only :11434) ==="
echo "Expect curl to work ONLY while Windows/Minisforum has:"
echo "  ssh -N -R 11434:127.0.0.1:11434 lew@192.168.68.93"
if curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags >/tmp/ollama-tags.json 2>/tmp/ollama-tags.err; then
  echo "OK: http://127.0.0.1:11434/api/tags reachable (should be Minisforum via tunnel)"
  head -c 500 /tmp/ollama-tags.json; echo
  ss -tlnp 2>/dev/null | grep 11434 || netstat -tlnp 2>/dev/null | grep 11434 || true
else
  echo "WARN: :11434 not reachable — start/recheck the Minisforum SSH reverse tunnel, then:"
  echo "  curl -fsS http://127.0.0.1:11434/api/tags"
  cat /tmp/ollama-tags.err 2>/dev/null || true
fi

echo
echo "Done. Restart Hermes gateway/Docker after this so it reloads config."
echo "  # e.g. docker restart <hermes-container>   OR   hermes gateway restart"
