"""Автоматический эксперимент: LLM (через LiteRouter) -> SANY -> TLC -> лог обратно в LLM.

Примеры:
    python src/run_experiment.py dataset/easy_891_AsynchInterface
    python src/run_experiment.py --all
    python src/run_experiment.py --all --model deepseek-v4-pro-0813:free --max-iter 10

ВНИМАНИЕ: модель deepseek-v4-pro-0813:free на LiteRouter больше недоступна, прогоны в runs/ повторить нельзя.
Сохранённые ответы и логи являются первичными данными; для проверки без API: python src/verify_logs.py.

Правила эксперимента (см. PROTOCOL.md):
  * модель видит только description.txt, .cfg и логи SANY/TLC; папка gold/ НЕ читается;
  * шаблоны промптов лежат в src/prompts/;
  * всё логируется в runs/<модель>/<задача>/.

Ключ API берётся из переменной окружения LITEROUTER_API_KEY или из файла .env
(строка KEY=значение, либо просто ключ в первой непустой строке). .env не коммитится.
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from common import (ROOT, classify_sany, classify_tlc, find_jar, first_error_line, run_to_file,
                    sany_ok, tlc_ok, tlc_stats, write_results)

PROMPTS = Path(__file__).resolve().parent / "prompts"
DEFAULT_MODEL = "deepseek-v4-pro-0813:free"
DEFAULT_BASE_URL = "https://api.literouter.com/v1"
TLC_TIMEOUT = 600
SANY_TIMEOUT = 120
TIMEOUT_TAIL_LINES = 100
API_RETRIES = 5

# Строки, которые попадают в промпт модели: не переводить, они зафиксированы в prompt_N.md прогонов
MSG_NO_CODE_BLOCK = "SANY was not run: the response did not contain a ```tla code block."
MSG_TLC_TIMEOUT = ("[NOTE: TLC was stopped by the {timeout} s timeout. The log is truncated: "
                   "only the last {lines} lines are shown.]\n{tail}")


# ------------------------------------------------------------------- утилиты
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
    sys.exit("Не найден ключ API: задайте LITEROUTER_API_KEY или создайте файл .env")


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
            log(f"API HTTP {e.code} (попытка {attempt}/{API_RETRIES}): {err}")
            if not retry:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log(f"Ошибка соединения с API (попытка {attempt}/{API_RETRIES}): {e}")
        if attempt < API_RETRIES:
            delay = min(60, 5 * 2 ** (attempt - 1))
            log(f"повтор через {delay} с")
            time.sleep(delay)
    raise RuntimeError("API недоступен после всех повторов")


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


# ----------------------------------------------------------------- одна задача
def run_task(task, args, jar, key):
    task = Path(task)
    cfgs = list(task.glob("*.cfg"))
    if len(cfgs) != 1 or not (task / "description.txt").exists():
        sys.exit(f"{task}: в папке задачи нужны description.txt и ровно один .cfg")
    mod = cfgs[0].stem
    # папка gold/ намеренно не читается нигде в этом скрипте
    description = (task / "description.txt").read_text(encoding="utf8").strip()
    cfg_content = cfgs[0].read_text(encoding="utf8").strip()

    slug = re.sub(r"[^\w.\-]+", "_", args.model)
    out = Path(args.out) / slug / task.name
    if out.exists() and any(out.iterdir()):
        if not args.force:
            print(f"ПРОПУСК {task.name}: папка {out} уже существует (--force сохранит её копию в runs/.backup и начнёт заново)")
            return None
        backup = Path(args.out) / ".backup" / slug / f"{task.name}_{datetime.now():%Y%m%d_%H%M%S}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(backup))
        print(f"Старый прогон перенесён в {backup}")
    out.mkdir(parents=True)
    work = out / "work"
    work.mkdir()
    shutil.copy(cfgs[0], work / f"{mod}.cfg")
    log = Logger(out / "run.log")

    t_generate = (PROMPTS / "1_generate.md").read_text(encoding="utf8")
    t_sany = (PROMPTS / "2_sany_error.md").read_text(encoding="utf8")
    t_tlc = (PROMPTS / "3_tlc_error.md").read_text(encoding="utf8")

    log(f"=== задача={task.name} модуль={mod} модель={args.model} макс_итераций={args.max_iter} ===")
    summary = {"task": task.name, "module": mod, "model_requested": args.model,
               "base_url": args.base_url, "started": datetime.now().isoformat(timespec="seconds"),
               "sany_pass_iter": None, "tlc_pass_iter": None, "total_iterations": 0,
               "status": "failed_max_iter", "final_tlc": None}
    rows = []
    messages = []
    prompt = fill(t_generate, DESCRIPTION=description, CFG_CONTENT=cfg_content, MODULE_NAME=mod)

    for n in range(1, args.max_iter + 1):
        log(f"--- итерация {n}: отправка промпта ({len(prompt)} симв.)")
        messages.append({"role": "user", "content": prompt})
        (out / f"prompt_{n}.md").write_text(prompt, encoding="utf8")
        try:
            data, elapsed = chat(messages, args.model, args.base_url, key, args.temperature, log)
        except Exception as e:
            log(f"Сбой API, задача прервана: {e}")
            summary["status"] = "api_error"
            break
        (out / f"api_{n}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
        msg = data["choices"][0]["message"]
        reply = msg.get("content") or ""
        summary["model_returned"] = data.get("model")
        if summary["model_returned"] is None:
            log("API не вернул поле model: фактическая модель ответом не подтверждена")
        log(f"ответ получен за {elapsed:.1f} с, {len(reply)} симв., usage={data.get('usage')}")
        (out / f"response_{n}.md").write_text(reply, encoding="utf8")
        messages.append({"role": "assistant", "content": reply})
        summary["total_iterations"] = n

        spec = extract_spec(reply)
        if spec is None:
            log("в ответе нет блока ```tla")
            rows.append({"n": n, "sany": "fail", "tlc": "–", "type": "нет блока кода",
                         "what": "в ответе нет ```tla блока"})
            spec_text = reply
            sany_log = MSG_NO_CODE_BLOCK
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
        log(f"SANY {'ok' if ok else 'ОШИБКА'} (код={rc}, {time.time() - t0:.1f} с)")
        if not ok:
            etype = classify_sany(sany_log)
            rows.append({"n": n, "sany": "fail", "tlc": "–", "type": etype,
                         "what": first_error_line(sany_log)})
            log(f"тип ошибки SANY: {etype}")
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
        log(f"TLC {'ok' if ok else 'таймаут' if timed_out else 'ОШИБКА'} "
            f"(код={rc}, {time.time() - t0:.1f} с) статистика={stats}")
        if ok:
            rows.append({"n": n, "sany": "ok", "tlc": "ok", "type": "–", "what": "–"})
            summary.update(tlc_pass_iter=n, status="passed", final_tlc=stats)
            break
        etype = classify_tlc(tlc_log, timed_out)
        rows.append({"n": n, "sany": "ok", "tlc": "timeout" if timed_out else "fail",
                     "type": etype, "what": first_error_line(tlc_log)})
        log(f"тип ошибки TLC: {etype}")
        sent_log = tlc_log
        if timed_out:
            tail = "\n".join(tlc_log.splitlines()[-TIMEOUT_TAIL_LINES:])
            sent_log = MSG_TLC_TIMEOUT.format(timeout=TLC_TIMEOUT, lines=TIMEOUT_TAIL_LINES, tail=tail)
        prompt = fill(t_tlc, CURRENT_SPEC=spec, CFG_CONTENT=cfg_content, FULL_TLC_LOG=sent_log)

    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    (out / "transcript.json").write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
    write_results(out, summary, rows)
    if summary["status"] == "failed_max_iter":
        (out / "failure_analysis.md").write_text(
            f"# Разбор причин неудачи: {task.name}\n\n"
            f"Модель не получила спецификацию, проходящую SANY и TLC за {args.max_iter} итераций.\n"
            "Заполнить вручную по таблице ошибок (results.md) и логам sany_N.log / tlc_N.log:\n\n"
            "- какие типы ошибок повторялись;\n- зацикливалась ли модель на одной ошибке;\n"
            "- почему не смогла исправить (синтаксис, непонимание семантики, конфигурация и т. д.).\n",
            encoding="utf8")
    log(f"=== завершено: статус={summary['status']} SANY@{summary['sany_pass_iter']} "
        f"TLC@{summary['tlc_pass_iter']} всего итераций={summary['total_iterations']} ===")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks", nargs="*", help="папки задач (dataset/<задача>)")
    ap.add_argument("--all", action="store_true", help="все задачи из dataset/")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--base-url", default=os.environ.get("LITEROUTER_BASE_URL", DEFAULT_BASE_URL))
    ap.add_argument("--max-iter", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=None, help="по умолчанию не передаётся")
    ap.add_argument("--out", default=str(ROOT / "runs"))
    ap.add_argument("--force", action="store_true", help="начать заново: старый прогон переносится в runs/.backup")
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
