from __future__ import annotations

import json
import re
from pathlib import Path
from common import (
    DATASET_DIR,
    RUNS_DIR,
    parse_tlc_metrics,
    extract_sany_error_summary,
    extract_tlc_error_summary,
)


def analyze_task_run(task_run_dir: Path, dataset_task_dir: Path) -> dict:
    task_name = task_run_dir.name
    level = "Easy" if task_name.startswith("easy_") else "Medium"
    source_url = ""
    src_file = dataset_task_dir / "source.txt"
    if src_file.exists():
        source_url = src_file.read_text(encoding="utf-8").strip()

    sany_logs = sorted(task_run_dir.glob("sany_*.log"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
    iterations = []
    first_sany_ok = None
    first_tlc_ok = None

    for s_log in sany_logs:
        it_num = int(re.findall(r"\d+", s_log.stem)[0])
        s_text = s_log.read_text(encoding="utf-8", errors="replace")
        s_summary = extract_sany_error_summary(s_text)
        s_ok = s_summary == "OK"
        if s_ok and first_sany_ok is None:
            first_sany_ok = it_num

        t_log = task_run_dir / f"tlc_{it_num}.log"
        if t_log.exists():
            t_text = t_log.read_text(encoding="utf-8", errors="replace")
            t_summary = extract_tlc_error_summary(t_text)
            t_ok = t_summary == "OK"
            if t_ok and first_tlc_ok is None:
                first_tlc_ok = it_num
        else:
            t_summary = "— (SANY failed)"
            t_ok = False

        iterations.append({
            "iter": it_num,
            "sany_ok": s_ok,
            "sany_msg": s_summary,
            "tlc_ok": t_ok,
            "tlc_msg": t_summary,
        })

    sem_logs_dir = task_run_dir / "semantic" / "logs"
    gen_metrics = parse_tlc_metrics((sem_logs_dir / "generated.log").read_text(encoding="utf-8", errors="replace")) if (sem_logs_dir / "generated.log").exists() else None
    gold_metrics = parse_tlc_metrics((sem_logs_dir / "gold.log").read_text(encoding="utf-8", errors="replace")) if (sem_logs_dir / "gold.log").exists() else None

    fwd_log = sem_logs_dir / "CompareFwd_GoldSpec.log"
    rev_log = sem_logs_dir / "CompareRev_GenSpec.log"
    fwd_status = extract_tlc_error_summary(fwd_log.read_text(encoding="utf-8", errors="replace")) if fwd_log.exists() else "N/A"
    rev_status = extract_tlc_error_summary(rev_log.read_text(encoding="utf-8", errors="replace")) if rev_log.exists() else "N/A"

    prop_checks = []
    if sem_logs_dir.exists():
        for plog in sorted(sem_logs_dir.glob("CompareFwd_Gold_*.log")):
            prop_name = plog.stem.replace("CompareFwd_Gold_", "")
            p_status = extract_tlc_error_summary(plog.read_text(encoding="utf-8", errors="replace"))
            prop_checks.append((prop_name, p_status))

    return {
        "task_name": task_name,
        "level": level,
        "source_url": source_url,
        "total_iters": len(iterations),
        "first_sany_ok": first_sany_ok,
        "first_tlc_ok": first_tlc_ok,
        "iterations": iterations,
        "gen_metrics": gen_metrics,
        "gold_metrics": gold_metrics,
        "fwd_status": fwd_status,
        "rev_status": rev_status,
        "prop_checks": prop_checks,
    }


def main() -> None:
    for model_dir in sorted(RUNS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        print(f"=== Проверка модели: {model_dir.name} ===")
        tasks_data = []
        for task_dir in sorted(model_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            ds_dir = DATASET_DIR / task_dir.name
            data = analyze_task_run(task_dir, ds_dir)
            tasks_data.append(data)
            print(
                f"  [{data['task_name']}] Итераций: {data['total_iters']} "
                f"(SANY OK: итер. {data['first_sany_ok']}, TLC OK: итер. {data['first_tlc_ok']}) | "
                f"Gen States: {data['gen_metrics'].distinct_states}/{data['gen_metrics'].total_states}/d={data['gen_metrics'].max_depth} vs "
                f"Gold: {data['gold_metrics'].distinct_states}/{data['gold_metrics'].total_states}/d={data['gold_metrics'].max_depth}"
            )

        out_md = model_dir / "REPORT_DATA.md"
        lines = [
            f"# Сводка экспериментальных данных для отчета ({model_dir.name})\n",
            "## 1. Общая таблица генерации и состояний (Пункты 3 и 4а)\n",
            "| Задача | Уровень | SANY (итер.) | TLC (итер.) | Всего итер. | Gen (Distinct / Total / Depth) | Gold (Distinct / Total / Depth) | Δ Distinct | Δ Total | Δ Depth |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
        for d in tasks_data:
            gm, goldm = d["gen_metrics"], d["gold_metrics"]
            d_dist = (gm.distinct_states - goldm.distinct_states) if (gm and goldm and gm.distinct_states is not None) else "N/A"
            d_tot = (gm.total_states - goldm.total_states) if (gm and goldm and gm.total_states is not None) else "N/A"
            d_dep = (gm.max_depth - goldm.max_depth) if (gm and goldm and gm.max_depth is not None) else "N/A"
            lines.append(
                f"| `{d['task_name']}` | {d['level']} | {d['first_sany_ok']} | {d['first_tlc_ok']} | {d['total_iters']} | "
                f"{gm.distinct_states} / {gm.total_states} / {gm.max_depth} | "
                f"{goldm.distinct_states} / {goldm.total_states} / {goldm.max_depth} | "
                f"{d_dist:+d} | {d_tot:+d} | {d_dep:+d} |"
            )

        lines.append("\n## 2. Таблица семантического сравнения через INSTANCE (Пункт 4б)\n")
        lines.append("| Задача | Прямое включение (`Gen => GoldSpec`) | Обратное включение (`Gold => GenSpec`) | Проверка отдельных свойств Gold на Gen |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for d in tasks_data:
            props_str = "<br>".join([f"`{p}`: {st}" for p, st in d["prop_checks"]]) if d["prop_checks"] else "—"
            lines.append(f"| `{d['task_name']}` | {d['fwd_status']} | {d['rev_status']} | {props_str} |")

        lines.append("\n## 3. Детализация по задачам (готовая фактура для текста отчета)\n")
        for d in tasks_data:
            lines.append(f"### Задача: `{d['task_name']}` ({d['level']})")
            lines.append(f"- **Источник:** {d['source_url']}")
            lines.append(f"- **Метрики итераций:** SANY пройден на {d['first_sany_ok']}-й итерации, TLC пройден на {d['first_tlc_ok']}-й итерации, всего итераций: {d['total_iters']}.")
            lines.append("- **Лог итераций (Пункт 3Б):**")
            for it in d["iterations"]:
                lines.append(f"  - *Итерация {it['iter']}:* SANY -> `{it['sany_msg']}` | TLC -> `{it['tlc_msg']}`")
            lines.append("")

        out_md.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n[OK] Файл с полными данными для отчета сохранен в: {out_md}\n")


if __name__ == "__main__":
    main()