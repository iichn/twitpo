"""Общие функции скриптов эксперимента: запуск SANY/TLC, разбор логов, форматирование результатов."""
import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ окружение
def find_jar():
    for p in (ROOT / "tla2tools.jar", ROOT / "tools" / "tla2tools.jar"):
        if p.exists():
            return p
    sys.exit("Не найден tla2tools.jar (положите его в корень репозитория или в tools/)")


def list_run_dirs():
    """Папки прогонов runs/<модель>; служебные (.backup, _*) пропускаются."""
    runs = ROOT / "runs"
    return sorted(p for p in runs.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def latest_run_dir():
    dirs = list_run_dirs()
    if not dirs:
        sys.exit("В runs/ нет прогонов")
    return dirs[-1]


def run_to_file(cmd, cwd, out_path, timeout):
    """Запускает команду, пишет stdout+stderr в файл. Возвращает (код возврата, был ли таймаут)."""
    with open(out_path, "w", encoding="utf8", errors="replace") as f:
        try:
            p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            return p.returncode, False
        except subprocess.TimeoutExpired:
            return None, True


# -------------------------------------------------------------- разбор логов
# SANY возвращает код 0 даже при ошибках, поэтому успех определяется по маркерам в логе
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


def classify_tlc(log, timed_out=False):
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
    # берётся последняя строка статистики: в промежуточных «Progress» числа печатаются с разделителем тысяч
    gens = re.findall(r"(\d+) states generated, (\d+) distinct states found", log)
    depth = re.search(r"depth of the complete state graph search is (\d+)", log)
    gen = gens[-1] if gens else None
    return {"states_generated": int(gen[0]) if gen else None,
            "distinct_states": int(gen[1]) if gen else None,
            "depth": int(depth.group(1)) if depth else None}


def tlc_status(log):
    """Итог запуска TLC: timeout / pass / fail: <первая строка ошибки>."""
    if "TIMEOUT" in log:
        return "timeout"
    if tlc_ok(log):
        return "pass"
    err = next((l.strip() for l in log.splitlines() if l.startswith("Error:")), "неизвестная ошибка")
    return "fail: " + err


def first_error_line(log):
    pats = [r"^Error:.*", r"^Unknown operator.*", r"^The operator.*", r"^File name.*",
            r"^Cannot find source.*", r"^line \d+.*", r"^Was expecting.*", r".*Encountered.*"]
    lines = [l.strip() for l in log.splitlines() if l.strip()]
    for p in pats:
        for i, l in enumerate(lines):
            if re.match(p, l):
                nxt = lines[i + 1] if l.startswith("line ") and i + 1 < len(lines) else ""
                return (l + (" " + nxt if nxt else ""))[:200]
    return (lines[-1] if lines else "")[:200]


def tool_versions(run_dir):
    """Версия TLC и окружение Java из первого найденного лога TLC прогона."""
    for p in sorted(Path(run_dir).glob("*/tlc_*.log")):
        text = p.read_text(encoding="utf8", errors="replace")
        v = re.search(r"TLC2 Version [^\r\n]+", text)
        env = re.search(r"\(([^()]*(?:Windows|Linux|Mac)[^()]*?)(?:, MSB[^()]*)?\)", text)
        if v:
            return v.group(0).strip(), (env.group(1) if env else None)
    return None, None


# --------------------------------------------------- форматирование результатов
def write_results(out, summary, rows):
    """results.md и results.csv по таблице итераций."""
    md = [f"# {summary['task']} ({summary['model_requested']})", "",
          "| № | SANY | TLC | Тип ошибки | Что сломано |",
          "|---|------|-----|------------|-------------|"]
    for r in rows:
        md.append(f"| {r['n']} | {r['sany']} | {r['tlc']} | {r['type']} | {r['what'].replace('|', chr(92) + '|')} |")
    md += ["", f"- SANY прошёл на итерации: {summary['sany_pass_iter']}",
           f"- TLC прошёл на итерации: {summary['tlc_pass_iter']}",
           f"- Всего итераций: {summary['total_iterations']}",
           f"- Финальный вывод TLC: {summary['final_tlc']}", ""]
    Path(out, "results.md").write_text("\n".join(md), encoding="utf8", newline="\n")
    with open(Path(out, "results.csv"), "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=["n", "sany", "tlc", "type", "what"])
        w.writeheader()
        w.writerows(rows)


def check_label(module, name, kind):
    """Русское название проверки семантического сравнения."""
    if module == "CompareFwd" and name == "GoldSpec":
        return "Refinement: сгенерированная ⇒ Gold (PROPERTY GoldSpec)"
    if module == "CompareRev":
        return "Обратный refinement: Gold ⇒ сгенерированная"
    what = "Инвариант" if kind == "INVARIANT" else "Свойство"
    return f"{what} Gold!{name.removeprefix('Gold_')} на поведениях сгенерированной спецификации"


def semantic_md(task, results, pass_iter):
    g, s = results["gold"], results["generated"]
    md = [f"# Семантическое сравнение: {task}", "",
          "## а) Размер пространства состояний", "",
          "| Спецификация | Distinct states | States generated | Max depth |", "|---|---|---|---|",
          f"| Gold | {g['distinct_states']} | {g['states_generated']} | {g['depth']} |",
          f"| Сгенерированная (итерация {pass_iter}) | {s['distinct_states']} | {s['states_generated']} | {s['depth']} |",
          "", "## б–г) Проверки через TLC", "", "| Проверка | Результат |", "|---|---|"]
    md += [f"| {c['check']} | {c['status']} |" for c in results["checks"]]
    return "\n".join(md) + "\n"


# ------------------------------------------- совместимость со сводным скриптом verify_logs.py
from dataclasses import dataclass

DATASET_DIR = ROOT / "dataset"
RUNS_DIR = ROOT / "runs"


@dataclass
class StateMetrics:
    distinct_states: "int | None" = None
    total_states: "int | None" = None
    max_depth: "int | None" = None


def parse_tlc_metrics(log_text):
    s = tlc_stats(log_text)
    return StateMetrics(s["distinct_states"], s["states_generated"], s["depth"])


def extract_sany_error_summary(log_text):
    if sany_ok(log_text):
        return "OK"
    keys = ["Lexical error", "Encountered", "Was expecting", "Unknown operator", "Multiply-defined", "Level error", "aborting"]
    errs = [l.strip() for l in log_text.splitlines() if any(k in l for k in keys)]
    return "; ".join(errs[:2]) if errs else "Ошибка синтаксиса или семантики в SANY"


def extract_tlc_error_summary(log_text):
    if tlc_ok(log_text):
        return "OK"
    m = re.search(r"Error:\s*(.+)", log_text)
    if not m:
        return "Ошибка выполнения или конфигурации TLC"
    steps = len(re.findall(r"^State\s+\d+\s*:", log_text, flags=re.MULTILINE))
    return f"{m.group(1).strip()} (длина трассы: {steps} состояний)" if steps else m.group(1).strip()
