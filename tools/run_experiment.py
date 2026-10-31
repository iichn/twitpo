"""Автоматический эксперимент: LLM (через LiteRouter) -> SANY -> TLC -> лог обратно в LLM.

Примеры:
    python tools/run_experiment.py dataset/easy_891_AsynchInterface
    python tools/run_experiment.py --all
    python tools/run_experiment.py --all --model deepseek-v4-pro-0813:free --max-iter 10

Правила эксперимента (см. PROTOCOL.md):
  * модель видит только description.txt, .cfg и логи SANY/TLC; папка gold/ НЕ читается;
  * шаблоны промптов лежат в tools/prompts/;
  * всё логируется в runs/<модель>/<задача>/.

Ключ API берётся из переменной окружения LITEROUTER_API_KEY или из файла .env
(строка KEY=значение, либо просто ключ в первой непустой строке). .env не коммитится.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = Path(__file__).resolve().parent / "prompts"
DEFAULT_MODEL = "deepseek-v4-pro-0813:free"
DEFAULT_BASE_URL = "https://api.literouter.com/v1"
TLC_TIMEOUT = 600
SANY_TIMEOUT = 120
TIMEOUT_TAIL_LINES = 100
API_RETRIES = 5

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- utilities
def find_jar():
    for p in (ROOT / "tla2tools.jar", ROOT / "tools" / "tla2tools.jar"):
        if p.exists():
            return p
    sys.exit("tla2tools.jar not found (put it in the repo root or tools/)")


def load_api_key():
    key = os.environ.get("LITEROUTER_API_KEY")
    if key:
        return key.strip()
    for env in (Path.cwd() / ".env", ROOT / ".env"):
        if not env.exists():
            continue
        lines = [l.strip() for l in env.read_text(encoding="utf8").splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        for l in lines:
            if "=" in l:
                k, v = l.split("=", 1)
                if k.strip() in ("LITEROUTER_API_KEY", "API_KEY", "OPENAI_API_KEY"):
                    return v.strip().strip("'\"")
        if lines and "=" not in lines[0]:
            return lines[0]
    sys.exit("API key not found: set LITEROUTER_API_KEY or create .env")


class Logger:
    def __init__(self, path):
        self.path = path

    def __call__(self, msg):
        line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
        print(line, flush=True)
        with open(self.path, "a", encoding="utf8") as f:
            f.write(line + "\n")


def fill(template, **values):
    # str.replace (не format), потому что в TLA+ коде много фигурных скобок
    for k, v in values.items():
        template = template.replace("{" + k + "}", v)
    return template


# ---------------------------------------------------------------------- LLM
def chat(messages, model, base_url, key, temperature, log):
    payload = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    body = json.dumps(payload).encode("utf8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", body,
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}",
         "User-Agent": "tla-llm-experiment/1.0"})
    for attempt in range(1, API_RETRIES + 1):
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                data = json.load(r)
            return data, time.time() - t0
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf8", "replace")[:500]
            retry = e.code in (408, 409, 425, 429) or e.code >= 500
            log(f"API HTTP {e.code} (attempt {attempt}/{API_RETRIES}): {err}")
            if not retry:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log(f"API connection error (attempt {attempt}/{API_RETRIES}): {e}")
        if attempt < API_RETRIES:
            delay = min(60, 5 * 2 ** (attempt - 1))
            log(f"retrying in {delay}s")
            time.sleep(delay)
    raise RuntimeError("API failed after retries")


def extract_spec(reply):
    """Последний ```tla-блок с целым модулем (иначе последний блок с MODULE, иначе последний блок)."""
    blocks = re.findall(r"```[ \t]*([A-Za-z+]*)[ \t]*\r?\n(.*?)```", reply, re.S)
    if not blocks:
        return None
    tla = [b for lang, b in blocks if lang.lower() in ("tla", "tla+", "tlaplus")]
    for pool in (tla, [b for _, b in blocks]):
        full = [b for b in pool if re.search(r"-{4,}\s*MODULE\s+\w+", b)]
        if full:
            return full[-1]
    return (tla or [b for _, b in blocks])[-1]


# ----------------------------------------------------------- SANY / TLC runs
def run_to_file(cmd, cwd, out_path, timeout):
    with open(out_path, "w", encoding="utf8", errors="replace") as f:
        try:
            p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            return p.returncode, False
        except subprocess.TimeoutExpired:
            return None, True


SANY_ERR = re.compile(r"Fatal errors|Semantic errors|\*\*\* Errors:|Could not parse|"
                      r"Abort messages|Parse Error|Lexical error", re.I)


def sany_ok(log):
    return not SANY_ERR.search(log)


def classify_sany(log):
    if re.search(r"does not match the name .* of the top level module", log):
        return "имя модуля не совпало с файлом"
    if re.search(r"Cannot find source file for module", log):
        return "выдуманный оператор или модуль (модуль не найден)"
    if re.search(r"Unknown operator|not defined|Could not resolve|undefined", log, re.I):
        return "неопределённое имя"
    if re.search(r"requires \d+ argument|number of arguments|wrong number", log, re.I):
        return "неверное число аргументов"
    if re.search(r"level", log, re.I) and re.search(r"error", log, re.I):
        return "неверный уровень выражения"
    if re.search(r"Fatal errors while parsing|Was expecting|Encountered|Parse Error|Lexical", log, re.I):
        return "синтаксис"
    return "прочее (SANY)"


def classify_tlc(log, timed_out):
    if timed_out:
        return "timeout"
    if "Deadlock reached" in log:
        return "deadlock"
    if re.search(r"Invariant .* is violated", log):
        return "нарушение инварианта"
    if re.search(r"Temporal properties were violated|Action property .* is violated|"
                 r"Property .* is violated|Implied-temporal", log):
        return "нарушение temporal-свойства"
    if re.search(r"configuration file|not assigned a value|Unknown constant|"
                 r"is not defined in the (spec|module)|specified in the configuration", log, re.I):
        return "ошибка конфигурации"
    if re.search(r"Error:|exception|Attempted to|evaluat|not completely specified|"
                 r"is either undefined|domain", log, re.I):
        return "ошибка вычисления"
    return "прочее (TLC)"


def tlc_ok(log):
    return "Model checking completed. No error has been found." in log


def tlc_stats(log):
    gen = re.search(r"(\d+) states generated, (\d+) distinct states found", log)
    depth = re.search(r"depth of the complete state graph search is (\d+)", log)
    return {"states_generated": int(gen.group(1)) if gen else None,
            "distinct_states": int(gen.group(2)) if gen else None,
            "depth": int(depth.group(1)) if depth else None}


def first_error_line(log, kind):
    pats = [r"^Error:.*", r"^Unknown operator.*", r"^The operator.*", r"^File name.*",
            r"^Cannot find source.*", r"^line \d+.*", r"^Was expecting.*", r".*Encountered.*"]
    lines = [l.strip() for l in log.splitlines() if l.strip()]
    for p in pats:
        for i, l in enumerate(lines):
            if re.match(p, l):
                nxt = lines[i + 1] if l.startswith("line ") and i + 1 < len(lines) else ""
                return (l + (" " + nxt if nxt else ""))[:200]
    return (lines[-1] if lines else "")[:200]


# ------------------------------------------------------------------ one task
def run_task(task, args, jar, key):
    task = Path(task)
    cfgs = list(task.glob("*.cfg"))
    if len(cfgs) != 1 or not (task / "description.txt").exists():
        sys.exit(f"{task}: need description.txt and exactly one .cfg in the task folder")
    mod = cfgs[0].stem
    # gold/ намеренно не читается нигде в этом скрипте
    description = (task / "description.txt").read_text(encoding="utf8").strip()
    cfg_content = cfgs[0].read_text(encoding="utf8").strip()

    slug = re.sub(r"[^\w.\-]+", "_", args.model)
    out = Path(args.out) / slug / task.name
    if out.exists() and any(out.iterdir()):
        if not args.force:
            print(f"SKIP {task.name}: {out} already exists (use --force to overwrite)")
            return None
        shutil.rmtree(out)
    out.mkdir(parents=True)
    work = out / "work"
    work.mkdir()
    shutil.copy(cfgs[0], work / f"{mod}.cfg")
    log = Logger(out / "run.log")

    t_generate = (PROMPTS / "1_generate.md").read_text(encoding="utf8")
    t_sany = (PROMPTS / "2_sany_error.md").read_text(encoding="utf8")
    t_tlc = (PROMPTS / "3_tlc_error.md").read_text(encoding="utf8")

    log(f"=== task={task.name} module={mod} model={args.model} max_iter={args.max_iter} ===")
    summary = {"task": task.name, "module": mod, "model_requested": args.model,
               "base_url": args.base_url, "started": datetime.now().isoformat(timespec="seconds"),
               "sany_pass_iter": None, "tlc_pass_iter": None, "total_iterations": 0,
               "status": "failed_max_iter", "final_tlc": None}
    rows = []
    messages = []
    prompt = fill(t_generate, DESCRIPTION=description, CFG_CONTENT=cfg_content, MODULE_NAME=mod)

    for n in range(1, args.max_iter + 1):
        log(f"--- iteration {n}: sending prompt ({len(prompt)} chars)")
        messages.append({"role": "user", "content": prompt})
        (out / f"prompt_{n}.md").write_text(prompt, encoding="utf8")
        try:
            data, elapsed = chat(messages, args.model, args.base_url, key, args.temperature, log)
        except Exception as e:
            log(f"API FAILURE, aborting task: {e}")
            summary["status"] = "api_error"
            break
        (out / f"api_{n}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
        msg = data["choices"][0]["message"]
        reply = msg.get("content") or ""
        summary["model_returned"] = data.get("model")
        log(f"response received in {elapsed:.1f}s, {len(reply)} chars, usage={data.get('usage')}")
        (out / f"response_{n}.md").write_text(reply, encoding="utf8")
        messages.append({"role": "assistant", "content": reply})
        summary["total_iterations"] = n

        spec = extract_spec(reply)
        if spec is None:
            log("no ```tla block found in the response")
            rows.append({"n": n, "sany": "fail", "tlc": "–", "type": "нет блока кода",
                         "what": "в ответе нет ```tla блока"})
            spec_text = reply
            sany_log = "SANY was not run: the response did not contain a ```tla code block."
            (out / f"sany_{n}.log").write_text(sany_log, encoding="utf8")
            (out / f"spec_iter{n}.tla").write_text(spec_text, encoding="utf8")
            prompt = fill(t_sany, CURRENT_SPEC=spec_text, FULL_SANY_LOG=sany_log)
            continue

        (out / f"spec_iter{n}.tla").write_text(spec, encoding="utf8", newline="")
        (work / f"{mod}.tla").write_text(spec, encoding="utf8", newline="")

        sany_path = out / f"sany_{n}.log"
        t0 = time.time()
        rc, _ = run_to_file(["java", "-cp", str(jar), "tla2sany.SANY", f"{mod}.tla"],
                            work, sany_path, SANY_TIMEOUT)
        sany_log = sany_path.read_text(encoding="utf8", errors="replace")
        ok = sany_ok(sany_log)
        log(f"SANY {'ok' if ok else 'FAIL'} (rc={rc}, {time.time() - t0:.1f}s)")
        if not ok:
            etype = classify_sany(sany_log)
            rows.append({"n": n, "sany": "fail", "tlc": "–", "type": etype,
                         "what": first_error_line(sany_log, "sany")})
            log(f"SANY error type: {etype}")
            prompt = fill(t_sany, CURRENT_SPEC=spec, FULL_SANY_LOG=sany_log)
            continue
        if summary["sany_pass_iter"] is None:
            summary["sany_pass_iter"] = n

        tlc_path = out / f"tlc_{n}.log"
        t0 = time.time()
        rc, timed_out = run_to_file(
            ["java", "-cp", str(jar), "tlc2.TLC", "-config", f"{mod}.cfg", "-workers", "auto", f"{mod}.tla"],
            work, tlc_path, TLC_TIMEOUT)
        shutil.rmtree(work / "states", ignore_errors=True)
        tlc_log = tlc_path.read_text(encoding="utf8", errors="replace")
        ok = (not timed_out) and tlc_ok(tlc_log)
        stats = tlc_stats(tlc_log)
        log(f"TLC {'ok' if ok else 'timeout' if timed_out else 'FAIL'} "
            f"(rc={rc}, {time.time() - t0:.1f}s) stats={stats}")
        if ok:
            rows.append({"n": n, "sany": "ok", "tlc": "ok", "type": "–", "what": "–"})
            summary.update(tlc_pass_iter=n, status="passed", final_tlc=stats)
            break
        etype = classify_tlc(tlc_log, timed_out)
        rows.append({"n": n, "sany": "ok", "tlc": "timeout" if timed_out else "fail",
                     "type": etype, "what": first_error_line(tlc_log, "tlc")})
        log(f"TLC error type: {etype}")
        sent_log = tlc_log
        if timed_out:
            tail = "\n".join(tlc_log.splitlines()[-TIMEOUT_TAIL_LINES:])
            sent_log = (f"[NOTE: TLC was stopped by the {TLC_TIMEOUT} s timeout. The log is truncated: "
                        f"only the last {TIMEOUT_TAIL_LINES} lines are shown.]\n{tail}")
        prompt = fill(t_tlc, CURRENT_SPEC=spec, CFG_CONTENT=cfg_content, FULL_TLC_LOG=sent_log)

    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    (out / "transcript.json").write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
    write_table(out, summary, rows)
    if summary["status"] == "failed_max_iter":
        (out / "failure_analysis.md").write_text(
            f"# Разбор причин неудачи: {task.name}\n\n"
            f"Модель не получила спецификацию, проходящую SANY и TLC за {args.max_iter} итераций.\n"
            "Заполнить вручную по таблице ошибок (results.md) и логам sany_N.log / tlc_N.log:\n\n"
            "- какие типы ошибок повторялись;\n- зацикливалась ли модель на одной ошибке;\n"
            "- почему не смогла исправить (синтаксис, непонимание семантики, конфигурация и т. д.).\n",
            encoding="utf8")
    log(f"=== done: status={summary['status']} sany_pass_iter={summary['sany_pass_iter']} "
        f"tlc_pass_iter={summary['tlc_pass_iter']} total={summary['total_iterations']} ===")
    return summary


def write_table(out, summary, rows):
    md = [f"# {summary['task']} ({summary['model_requested']})", "",
          "| № | SANY | TLC | Тип ошибки | Что сломано (авто: первая строка ошибки из лога) |",
          "|---|------|-----|------------|-----------------------------------------------|"]
    for r in rows:
        what = r["what"].replace("|", "\\|")
        md.append(f"| {r['n']} | {r['sany']} | {r['tlc']} | {r['type']} | {what} |")
    md += ["", f"- SANY прошёл на итерации: {summary['sany_pass_iter']}",
           f"- TLC прошёл на итерации: {summary['tlc_pass_iter']}",
           f"- Всего итераций: {summary['total_iterations']}",
           f"- Финальный вывод TLC: {summary['final_tlc']}", ""]
    (out / "results.md").write_text("\n".join(md), encoding="utf8")
    with open(out / "results.csv", "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=["n", "sany", "tlc", "type", "what"])
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks", nargs="*", help="папки задач (dataset/<задача>)")
    ap.add_argument("--all", action="store_true", help="все задачи из dataset/")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--base-url", default=os.environ.get("LITEROUTER_BASE_URL", DEFAULT_BASE_URL))
    ap.add_argument("--max-iter", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=None, help="по умолчанию не передаётся")
    ap.add_argument("--out", default=str(ROOT / "runs"))
    ap.add_argument("--force", action="store_true", help="перезаписать существующий прогон")
    args = ap.parse_args()

    tasks = list(args.tasks)
    if args.all:
        tasks = sorted(str(p) for p in (ROOT / "dataset").iterdir() if p.is_dir())
    if not tasks:
        ap.error("укажите папки задач или --all")
    jar, key = find_jar(), load_api_key()
    results = [r for r in (run_task(t, args, jar, key) for t in tasks) if r]
    print("\nИТОГ:")
    for s in results:
        print(f"  {s['task']}: {s['status']}, SANY@{s['sany_pass_iter']}, "
              f"TLC@{s['tlc_pass_iter']}, итераций {s['total_iterations']}")


if __name__ == "__main__":
    main()
