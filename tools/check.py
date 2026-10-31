"""Прогон SANY и TLC для одной итерации.

Использование:
    python tools\check.py <папка_задачи> <файл_с_ответом_модели.tla> <номер_итерации>

Пример:
    python tools\check.py dataset\easy_891_AsynchInterface answer.tla 1

Результат: <папка_задачи>\iterations\iterNN\ с .tla, .cfg, sany.log, tlc.log, result.json
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
JAR = next((p for p in (_here / "tla2tools.jar", _here.parent / "tla2tools.jar") if p.exists()), _here / "tla2tools.jar")
TLC_TIMEOUT = 300


def run(cls, args, cwd):
    try:
        p = subprocess.run(
            ["java", "-cp", str(JAR), cls, *args],
            cwd=cwd, capture_output=True, text=True,
            encoding="utf8", errors="ignore", timeout=TLC_TIMEOUT,
        )
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    task, answer, it = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    text = answer.read_text(encoding="utf8")
    m = re.search(r"-+\s*MODULE\s+(\w+)", text)
    if not m:
        sys.exit("В файле нет заголовка '---- MODULE Имя ----'")
    mod = m.group(1)

    cfgs = [c for c in task.glob("*.cfg")]
    if len(cfgs) != 1:
        sys.exit("В папке задачи должен быть ровно один .cfg")

    out = task / "iterations" / f"iter{it:02d}"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{mod}.tla").write_text(text, encoding="utf8")
    shutil.copy(cfgs[0], out / f"{mod}.cfg")

    _, sany = run("tla2sany.SANY", [f"{mod}.tla"], out)
    (out / "sany.log").write_text(sany, encoding="utf8")
    sany_ok = "Error" not in sany and "error" not in sany.lower().replace("0 errors", "")
    res = {"iteration": it, "module": mod, "sany_ok": sany_ok}

    if sany_ok:
        _, tlc = run("tlc2.TLC", ["-workers", "4", f"{mod}.tla"], out)
        (out / "tlc.log").write_text(tlc, encoding="utf8")
        gen = re.search(r"(\d+) states generated, (\d+) distinct states found", tlc)
        depth = re.search(r"depth of the complete state graph search is (\d+)", tlc)
        ok = "Model checking completed. No error has been found." in tlc
        res.update(
            tlc_ok=ok,
            states_generated=int(gen.group(1)) if gen else None,
            distinct_states=int(gen.group(2)) if gen else None,
            max_depth=int(depth.group(1)) if depth else None,
        )
        if not ok:
            res["tlc_first_error"] = next(
                (l for l in tlc.splitlines() if l.startswith("Error:")), "см. tlc.log")
    (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"Logs: {out}")


if __name__ == "__main__":
    main()
