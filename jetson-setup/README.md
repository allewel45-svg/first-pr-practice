# Jetson: remove local Ollama

Hermes on the Jetson must talk only to Ollama on the Minisforum (AI X1 Pro-470) through the SSH reverse tunnel.

## Run on Jetson as `lew`

```bash
# copy this folder to the Jetson, then:
cd jetson-setup
chmod +x remove-local-ollama.sh
./remove-local-ollama.sh
```

Then restart Hermes (Docker container or `hermes gateway`).

## What the script does

1. Stops/disables/masks `ollama.service`
2. Deletes `/usr/local/bin/ollama`, `/usr/share/ollama`, `~/.ollama`, and the `ollama` user/group
3. Removes any Docker containers/images named ollama
4. Sets Hermes to:
   - `model.provider = custom`
   - `model.base_url = http://127.0.0.1:11434/v1`
   - `model.default = qwen3.5-4b-64k` (if unset / cloud leftover)
5. Comments cloud LLM keys in `~/.hermes/.env` if present

## Keep the Minisforum tunnel up

On the Minisforum (Windows), Ollama must keep reverse-forwarding to the Jetson:

```powershell
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -R 11434:127.0.0.1:11434 lew@192.168.68.93
```

(Prefer your existing self-healing / logon task if you already have one.)

## Pass criteria

| Check | Expected |
|-------|----------|
| `command -v ollama` | empty |
| `ls /usr/share/ollama ~/.ollama` | missing |
| `curl http://127.0.0.1:11434/api/tags` | lists Minisforum models (`qwen3.5-4b-64k`, etc.) **only while tunnel is up** |
| Hermes replies | uses Minisforum model, not a Jetson-local one |

Note: an earlier session already reported Jetson Ollama removed (~13 GB freed). Re-run this anytime to wipe leftovers or confirm the Minisforum-only path.
