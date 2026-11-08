"""Семантическое сравнение сгенерированной и Gold спецификаций (п. 4 задания).

    python src/compare_gold.py                       # все задачи, последний прогон в runs/
    python src/compare_gold.py --run runs/<модель> [--task easy_891_AsynchInterface]

Для каждой задачи:
  а) TLC (-workers 1, чтобы глубина была детерминированной) на Gold и на финальной сгенерированной
     спецификации: distinct / generated / depth;
  б) refinement «сгенерированная => Gold»: Gold == INSTANCE SpecGold WITH ...; GoldSpec == Gold!Spec; PROPERTY GoldSpec;
  в) доп. проверки: инварианты и свойства Gold на поведениях сгенерированной спецификации;
  г) обратный refinement «Gold => сгенерированная» (какое поведение Gold модель потеряла).
Подстановки переменных вручную записаны в src/semantic/<задача>.json.
Gold используется только здесь, после завершения генерации.
Результаты: <прогон>/<задача>/semantic/ (логи, обёртки, semantic.md, semantic.json).
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from common import ROOT, check_label, find_jar, latest_run_dir, semantic_md, tlc_stats, tlc_status

TLC_TIMEOUT = 600


def run_tlc(cwd, module, cfg, log_path, workers="auto"):
    cmd = ["java", "-cp", str(find_jar()), "tlc2.TLC", "-config", cfg, "-workers", workers, module + ".tla"]
    with open(log_path, "w", encoding="utf8", errors="replace") as f:
        try:
            subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=TLC_TIMEOUT)
        except subprocess.TimeoutExpired:
            f.write("\nTIMEOUT\n")
    shutil.rmtree(Path(cwd) / "states", ignore_errors=True)
    return Path(log_path).read_text(encoding="utf8", errors="replace")


def parse(log):
    return {"status": tlc_status(log), **tlc_stats(log)}


def cfg_constants(cfg_text):
    """Оставить из исходного .cfg только CONSTANT(S) и CHECK_DEADLOCK."""
    text = re.sub(r"\(\*.*?\*\)", "", cfg_text, flags=re.S)
    text = re.sub(r"\\\*.*", "", text)
    keys = r"(SPECIFICATION|INVARIANTS?|PROPERT(?:Y|IES)|CONSTANTS?|CONSTRAINTS?|ACTION_CONSTRAINTS?|" \
           r"SYMMETRY|INIT|NEXT|VIEW|ALIAS|CHECK_DEADLOCK|POSTCONDITION)\b"
    keep, current = [], None
    for line in text.splitlines():
        m = re.match(r"\s*" + keys, line)
        if m:
            current = m.group(1)
        if current in ("CONSTANT", "CONSTANTS", "CHECK_DEADLOCK") and line.strip():
            keep.append(line.rstrip())
    return "\n".join(keep)


def with_clause(subst):
    return ",\n    ".join(f"{k} <- {v}" for k, v in subst.items())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", help="папка прогона runs/<модель>")
    ap.add_argument("--task")
    args = ap.parse_args()
    run_dir = Path(args.run) if args.run else latest_run_dir()
    tasks = [args.task] if args.task else sorted(p.name for p in run_dir.iterdir() if p.is_dir())

    for task in tasks:
        tdir, dataset = run_dir / task, ROOT / "dataset" / task
        summary = json.loads((tdir / "summary.json").read_text(encoding="utf8"))
        if summary["tlc_pass_iter"] is None:
            print(f"{task}: нет спецификации, прошедшей TLC, пропуск")
            continue
        mod = summary["module"]
        mapping = json.loads((ROOT / "src" / "semantic" / f"{task}.json").read_text(encoding="utf8"))
        sem = tdir / "semantic"
        if sem.exists():
            shutil.rmtree(sem)
        (sem / "logs").mkdir(parents=True)
        work = sem / "work"
        work.mkdir()

        gold_src = (dataset / "gold" / f"{mod}.tla").read_text(encoding="utf8")
        cfg_text = (dataset / f"{mod}.cfg").read_text(encoding="utf8")
        final = (tdir / f"spec_iter{summary['tlc_pass_iter']}.tla").read_text(encoding="utf8")
        consts = cfg_constants(cfg_text)

        results = {}
        # а) Gold и сгенерированная по отдельности, каждая со своим .cfg
        for label, text in (("gold", gold_src), ("generated", final)):
            d = work / label
            d.mkdir()
            (d / f"{mod}.tla").write_text(text, encoding="utf8", newline="")
            shutil.copy(dataset / f"{mod}.cfg", d / f"{mod}.cfg")
            results[label] = parse(run_tlc(d, mod, f"{mod}.cfg", sem / "logs" / f"{label}.log", workers="1"))
            print(f"{task} {label}: {results[label]}")

        # б, в, г) обёртки в общей папке
        d = work / "cmp"
        d.mkdir()
        (d / f"{mod}.tla").write_text(final, encoding="utf8", newline="")
        (d / "SpecGold.tla").write_text(
            re.sub(r"MODULE\s+\w+", "MODULE SpecGold", gold_src, count=1), encoding="utf8", newline="")

        fwd_ops = [("GoldSpec", f"Gold!{mapping['gold_spec']}", "PROPERTY", check_label("CompareFwd", "GoldSpec", "PROPERTY"))]
        for e in mapping.get("forward_extra", []):
            fwd_ops.append((f"Gold_{e['gold_name']}", f"Gold!{e['gold_name']}", e["kind"],
                            check_label("CompareFwd", f"Gold_{e['gold_name']}", e["kind"])))
        fwd = (f"---- MODULE CompareFwd ----\nEXTENDS {mod}\n"
               f"Gold == INSTANCE SpecGold WITH\n    {with_clause(mapping['forward_subst'])}\n"
               + "".join(f"{n} == {x}\n" for n, x, _, _ in fwd_ops) + "====\n")
        (d / "CompareFwd.tla").write_text(fwd, encoding="utf8")

        rev_ops = [("GenSpec", f"Gen!{mapping['gen_spec']}", "PROPERTY", check_label("CompareRev", "GenSpec", "PROPERTY"))]
        rev = (f"---- MODULE CompareRev ----\nEXTENDS SpecGold\n"
               f"Gen == INSTANCE {mod} WITH\n    {with_clause(mapping['reverse_subst'])}\n"
               + "".join(f"{n} == {x}\n" for n, x, _, _ in rev_ops) + "====\n")
        (d / "CompareRev.tla").write_text(rev, encoding="utf8")

        checks = [("CompareFwd", mapping["gen_spec"], op) for op in fwd_ops] + \
                 [("CompareRev", mapping["gold_spec"], op) for op in rev_ops]
        results["checks"] = []
        for module, spec, (name, _, kind, desc) in checks:
            cfg_name = f"{module}_{name}.cfg"
            (d / cfg_name).write_text(f"SPECIFICATION {spec}\n{consts}\n{kind} {name}\n", encoding="utf8")
            r = parse(run_tlc(d, module, cfg_name, sem / "logs" / f"{module}_{name}.log"))
            r.update(check=desc, name=name, module=module, kind=kind)
            results["checks"].append(r)
            print(f"{task} {desc}: {r['status']}")
        for f in d.glob("Compare*.tla"):
            shutil.copy(f, sem / f.name)
        for f in d.glob("Compare*.cfg"):
            shutil.copy(f, sem / f.name)
        shutil.copy(d / "SpecGold.tla", sem / "SpecGold.tla")
        shutil.rmtree(work)

        (sem / "semantic.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf8", newline="\n")
        (sem / "semantic.md").write_text(semantic_md(task, results, summary["tlc_pass_iter"]), encoding="utf8", newline="\n")
    print("готово")


if __name__ == "__main__":
    main()
