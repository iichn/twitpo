"""Автоматический цикл: LLM (OpenAI-совместимый API, напр. DeepSeek) -> SANY -> TLC -> лог обратно в LLM.

    set DEEPSEEK_API_KEY=sk-...
    python tools\run_llm.py dataset\easy_891_AsynchInterface --model deepseek-chat

Модель видит ТОЛЬКО description.txt, .cfg и логи SANY/TLC. Папка gold/ не читается.
Переменные окружения: LLM_BASE_URL (по умолчанию https://api.deepseek.com), DEEPSEEK_API_KEY.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import check  # noqa: E402

PROMPT = """Write a TLA+ specification for the system described below.

Requirements:
- The module name must be exactly `{mod}` (file {mod}.tla).
- The specification will be checked by SANY and then by TLC with the configuration file below, so it must define every name that the configuration file refers to, with exactly these names.
- Reply with the complete module in a single ```tla code block and nothing else.

## System description
{desc}

## TLC configuration file ({mod}.cfg)
```
{cfg}
```
"""

FEEDBACK_SANY = """SANY rejected the specification. Fix it and reply with the complete corrected module in a single ```tla code block.

SANY log:
```
{log}
```
"""

FEEDBACK_TLC = """The specification parses, but TLC reports a problem. Fix it and reply with the complete corrected module in a single ```tla code block.

TLC log:
```
{log}
```
"""


def chat(messages, model, temperature):
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
    key = os.environ.get("DEEPSEEK_API_KEY") or sys.exit("Set DEEPSEEK_API_KEY")
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    req = urllib.request.Request(
        base + "/chat/completions", body,
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"], data.get("model", model)


def extract_code(reply):
    m = re.search(r"```(?:tla\+?|tlaplus)?\s*\n(.*?)```", reply, re.S | re.I)
    return (m.group(1) if m else reply).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--max-iter", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=0.0)
    a = ap.parse_args()

    task = Path(a.task)
    cfg_path = next(task.glob("*.cfg"))
    mod = cfg_path.stem
    desc = (task / "description.txt").read_text(encoding="utf8").strip()
    cfg = cfg_path.read_text(encoding="utf8").strip()

    messages = [{"role": "user", "content": PROMPT.format(mod=mod, desc=desc, cfg=cfg)}]
    summary = {"task": task.name, "model_requested": a.model, "sany_pass_iter": None,
               "tlc_pass_iter": None, "iterations": []}

    for it in range(1, a.max_iter + 1):
        reply, model_used = chat(messages, a.model, a.temperature)
        summary["model_returned"] = model_used
        messages.append({"role": "assistant", "content": reply})
        res = check(task, extract_code(reply), it)
        out = Path(res["dir"])
        (out / "prompt.txt").write_text(messages[-2]["content"], encoding="utf8")
        (out / "reply.txt").write_text(reply, encoding="utf8")
        summary["iterations"].append({k: res.get(k) for k in
                                      ("iteration", "sany_ok", "tlc_ok", "tlc_first_error",
                                       "distinct_states", "states_generated", "max_depth")})
        print(f"[iter {it}] SANY={'ok' if res['sany_ok'] else 'FAIL'} "
              f"TLC={res.get('tlc_ok', 'not run')} {res.get('tlc_first_error', '')}")

        if res["sany_ok"] and summary["sany_pass_iter"] is None:
            summary["sany_pass_iter"] = it
        if not res["sany_ok"]:
            feedback = FEEDBACK_SANY.format(log=(out / "sany.log").read_text(encoding="utf8"))
        elif not res["tlc_ok"]:
            feedback = FEEDBACK_TLC.format(log=(out / "tlc.log").read_text(encoding="utf8"))
        else:
            summary["tlc_pass_iter"] = it
            break
        messages.append({"role": "user", "content": feedback})

    summary["total_iterations"] = len(summary["iterations"])
    (task / "iterations" / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
    (task / "iterations" / "transcript.json").write_text(
        json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({k: v for k, v in summary.items() if k != "iterations"}, indent=2))


if __name__ == "__main__":
    main()
