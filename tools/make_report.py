"""Сборка отчёта (вариант 1) в report/Отчет_вариант1.docx из результатов в runs/.

    python tools/make_report.py

Оформление: Times New Roman 12, заголовки 14, выравнивание по ширине, интервал 1.15.
Числа и таблицы берутся из runs/<модель>/<задача>/ (summary.json, results.csv, semantic/semantic.json).
"""
import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = "deepseek-v4-pro-0813_free"
RUNS = ROOT / "runs" / MODEL_DIR
REPO_URL = "https://github.com/iichn/twitpo/tree/variant1-dataset"
BENCH = "https://github.com/LUC-AI4FM/tla_benchmark/tree/dataset-release/dataset_release"
FONT = "Times New Roman"

TASKS = [  # (папка, уровень)
    ("easy_891_AsynchInterface", "легкий (basic)"),
    ("easy_1127_TCommit", "легкий (basic)"),
    ("medium_1000_SimpleAllocator", "средний (intermediate)"),
    ("medium_1067_SyncTerminationDetection", "средний (intermediate)"),
]
TITLES = {
    "easy_891_AsynchInterface": "AsynchInterface (асинхронный интерфейс «отправитель – получатель»)",
    "easy_1127_TCommit": "TCommit (транзакционный commit, менеджеры ресурсов)",
    "medium_1000_SimpleAllocator": "SimpleAllocator (распределитель ресурсов)",
    "medium_1067_SyncTerminationDetection": "SyncTerminationDetection (обнаружение завершения в кольце, EWD840)",
}

# ---- тексты анализа (по результатам прогона; см. runs/.../semantic) ----
PROMPT_INFO = (
    "В промпте содержалась информация о: текстовом описании системы (поле desc_declarative_gpt датасета), "
    "полном содержимом .cfg файла, обязательном имени модуля и требовании пройти SANY и TLC с этой конфигурацией; "
    "Gold-спецификация модели не показывалась. Использовались техники: zero-shot (примеры в промпте не давались) "
    "+ краткий Chain-of-Thought («think step by step briefly first»), диалог многошаговый (модель видит свои "
    "предыдущие ответы). На каждой итерации для исправления модели передавалось: текущая спецификация и ПОЛНЫЙ лог "
    "SANY (при ошибке парсинга) либо текущая спецификация, .cfg и ПОЛНЫЙ лог TLC (при ошибке model checking); "
    "никаких дополнительных подсказок не давалось."
)

SEM = {
    "easy_891_AsynchInterface": (
        "Число уникальных состояний совпало (12 и 12), но общее число сгенерированных состояний и глубина "
        "различаются (27 против 30 и 4 против 2). Причина в начальных состояниях: в Gold они допускают "
        "rdy ∈ {0,1}, ack = rdy (6 начальных состояний), а модель зафиксировала rdy = ack = FALSE (3 начальных "
        "состояния). Достижимое множество состояний при этом одинаково, различается только порядок обхода.",
        "Refinement «сгенерированная ⇒ Gold» выполняется: каждое поведение модели является поведением Gold при "
        "отображении BOOLEAN → {0,1} (rdy ↦ IF rdy THEN 1 ELSE 0). Инвариант Gold!TypeInvariant на поведениях модели "
        "выполняется. Обратная проверка «Gold ⇒ сгенерированная» нарушается уже в начальном состоянии: Gold допускает "
        "начало с rdy = ack = 1, а модель этого не допускает. Описание не фиксирует начальные значения "
        "рукопожатия, поэтому модель сделала неявное допущение и получила более узкую, но корректную спецификацию. "
        "Вывод: спецификация семантически корректна (корректное сужение Gold).",
    ),
    "easy_1127_TCommit": (
        "Число уникальных состояний больше, чем у Gold (46 против 34), общее число сгенерированных состояний близко "
        "(97 против 94), глубина одинакова (7). Лишние 12 состояний – это состояния, недостижимые в Gold, например "
        "когда один RM уже committed, а другой всё ещё working.",
        "Refinement «сгенерированная ⇒ Gold» НЕ выполняется. Контрпример TLC: r1 выполняет Prepare и затем Commit, "
        "пока r2 и r3 всё ещё в состоянии working. В Gold решение о commit разрешено только когда все RM в состоянии "
        "prepared или committed (предикат canCommit), в модели условие слабее (достаточно, чтобы никто не был aborted). "
        "Обратный refinement тоже нарушается: в Gold RM может выполнить abort из состояния working, а модель разрешает "
        "abort только из prepared. Инварианты Gold TCTypeOK и TCConsistent на поведениях модели выполняются, "
        "поэтому проверки из .cfg ошибку не обнаруживают: модель безопасна по TCConsistent, но нарушает логику "
        "двухфазной фиксации. В тексте описания условие canCommit явно не сформулировано, модель придумала своё.",
    ),
    "medium_1000_SimpleAllocator": (
        "Различие в пространстве состояний очень велико: 43 уникальных состояния против 400 у Gold (в ~9 раз меньше) и "
        "94 против 1633 сгенерированных. Глубина 5 против 6. Модель описывает существенно более узкое поведение.",
        "Refinement «сгенерированная ⇒ Gold» НЕ выполняется. Контрпример: клиент c1 запрашивает {r1, r2}, получает r1, "
        "после чего Return сбрасывает его невыполненный запрос {r2} (requested[c] = {}). В Gold Return не меняет unsat "
        "(UNCHANGED unsat), а описание прямо говорит, что клиент может вернуть ресурсы до полного удовлетворения "
        "запроса. Обратный refinement тоже нарушается. Дополнительно модель сузила поведение: запрос допустим только "
        "если ни у кого нет невыполненных запросов, ресурсы выделяются и возвращаются по одному (в Gold выделяется "
        "произвольное непустое подмножество). Из проверок свойств Gold на поведениях модели нарушается "
        "ClientsWillObtain; TypeInvariant, ResourceMutex, ClientsWillReturn и InfOftenSatisfied выполняются. "
        "Собственная версия ClientsWillObtain у модели (requested[c] ≠ {} ⇝ requested[c] = {}) практически тривиальна, "
        "потому что Return очищает запрос. "
        "Итерации 2–4 падали на liveness (starvation), и модель устранила это "
        "ослаблением спецификации (запрос допускается, только если ни у кого нет невыполненных запросов; выделение и "
        "возврат по одному ресурсу; сброс запроса при возврате) и собственных формулировок свойств. "
        "Вывод: спецификация проходит TLC, но семантически НЕ эквивалентна Gold и ослаблена.",
    ),
    "medium_1067_SyncTerminationDetection": (
        "Число уникальных состояний ровно вдвое больше, чем у Gold (258 против 129): модель ввела лишнюю булеву "
        "переменную tick, удваивающую пространство. Общее число сгенерированных состояний меньше (1860 против 3722), "
        "глубина 2 против 1. Меньшее число переходов объясняется более узкими действиями: пробуждение только "
        "следующего узла кольца и обнаружение завершения только отдельным действием Detect.",
        "Refinement «сгенерированная ⇒ Gold» выполняется (отображение active ↦ сдвиг индексов 1..N на 0..N-1, "
        "detected ↦ terminationDetected, переменная tick отбрасывается как не влияющая). Также на поведениях модели "
        "выполняются все свойства Gold: TypeOK, TDCorrect, Quiescence, Liveness. Обратная проверка нарушается в "
        "начальном состоянии: Gold допускает terminationDetected = TRUE сразу при всех неактивных узлах и произвольное "
        "пробуждение любым активным узлом любого другого (не только соседа). Переменная tick – артефакт: модель добавила "
        "защиту ~detected, получила deadlock (итерация 2) и «вылечила» его добавлением действия Tick; в Gold deadlock "
        "отсутствует по построению, потому что DetectTermination остаётся включённым. Слово «ring» из описания модель "
        "поняла как ограничение на пробуждение только соседа. Вывод: спецификация корректное сужение Gold, но с "
        "искусственной переменной.",
    ),
}

ERRORS_SANY_TLC = {
    "easy_891_AsynchInterface": (
        "ошибок не было (SANY и TLC пройдены с первой итерации)",
        "ошибок не было",
    ),
    "easy_1127_TCommit": (
        "ошибок не было (SANY пройден с первой итерации)",
        "ошибка вычисления на итерации 1: Init записан как предикат вместо присваивания, TLC не смог вычислить rmState",
    ),
    "medium_1000_SimpleAllocator": (
        "выдуманный оператор на итерации 1 (Union {...} вместо UNION), на итерации 2 SANY уже пройден",
        "нарушение temporal-свойства (starvation, liveness) на итерациях 2, 3 и 4; на итерации 5 TLC пройден",
    ),
    "medium_1067_SyncTerminationDetection": (
        "неопределённое имя (i') и конфликт имён (вспомогательный Next(i) и основной Next) на итерации 1",
        "deadlock на итерации 2 (после Detect ни одно действие не применимо); на итерации 3 TLC пройден",
    ),
}


# ---------------------------------------------------------------- docx utils
def set_font(run, size=12, bold=None, italic=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(a), FONT)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def fmt(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line=True, after=6):
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = 1.15
    pf.space_after = Pt(after)
    pf.space_before = Pt(0)
    if first_line and align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        pf.first_line_indent = Cm(1.25)


class Report:
    def __init__(self):
        self.d = Document()
        s = self.d.sections[0]
        s.left_margin, s.right_margin = Cm(3), Cm(1.5)
        s.top_margin = s.bottom_margin = Cm(2)
        st = self.d.styles["Normal"]
        st.font.name, st.font.size = FONT, Pt(12)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        self._footer()

    def _footer(self):
        p = self.d.sections[0].footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        set_font(r)
        for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
            if tag:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), tag)
            else:
                el = OxmlElement("w:instrText")
                el.set(qn("xml:space"), "preserve")
                el.text = text
            r._r.append(el)

    def heading(self, text, level=1):
        p = self.d.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.LEFT if level > 1 else WD_ALIGN_PARAGRAPH.CENTER, False, 6)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.keep_with_next = True
        set_font(p.add_run(text), 14, bold=True)

    def para(self, text, bold_prefix=None, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p = self.d.add_paragraph()
        fmt(p, align, indent)
        if bold_prefix:
            set_font(p.add_run(bold_prefix), bold=True)
        set_font(p.add_run(text))
        return p

    def bullet(self, text):
        p = self.d.add_paragraph()
        fmt(p, first_line=False, after=3)
        p.paragraph_format.left_indent = Cm(1.25)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        set_font(p.add_run("– " + text))

    def table(self, header, rows, widths=None, size=12):
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            c = t.rows[0].cells[i]
            c.paragraphs[0].text = ""
            set_font(c.paragraphs[0].add_run(str(h)), size, bold=True)
            fmt(c.paragraphs[0], WD_ALIGN_PARAGRAPH.LEFT, False, 0)
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].paragraphs[0].text = ""
                set_font(cells[i].paragraphs[0].add_run(str(v).replace("`", "")), size)
                fmt(cells[i].paragraphs[0], WD_ALIGN_PARAGRAPH.LEFT, False, 0)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def box(self, blocks):
        """Рамка в стиле шаблона из постановки: список (жирный_префикс, текст)."""
        t = self.d.add_table(rows=1, cols=1)
        t.style = "Table Grid"
        cell = t.rows[0].cells[0]
        first = True
        for prefix, text in blocks:
            p = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            fmt(p, WD_ALIGN_PARAGRAPH.JUSTIFY, False, 4)
            if prefix:
                set_font(p.add_run(prefix), bold=True)
            set_font(p.add_run(text))
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def load(task):
    d = RUNS / task
    summary = json.loads((d / "summary.json").read_text(encoding="utf8"))
    rows = list(csv.DictReader(open(d / "results.csv", encoding="utf8")))
    sem = json.loads((d / "semantic" / "semantic.json").read_text(encoding="utf8"))
    src = {}
    for line in (ROOT / "dataset" / task / "source.txt").read_text(encoding="utf8").splitlines():
        if line.startswith("spec_id="):
            src["spec_id"] = line.split("=", 1)[1].strip()
        elif ": " in line:
            k, v = line.split(": ", 1)
            src[k.strip()] = v.strip().replace("/tree/", "/blob/") if v.startswith("https://github.com/LUC") else v.strip()
    return summary, rows, sem, src


def main():
    data = {t: load(t) for t, _ in TASKS}
    r = Report()

    # --- титульный лист
    for text, size, bold, after in (
        ("Министерство науки и высшего образования Российской Федерации", 12, False, 40),
        ("Дисциплина: «Тестирование и верификация программного обеспечения»", 14, False, 80),
        ("ОТЧЁТ", 14, True, 12),
        ("Вариант №1", 14, True, 12),
        ("Определение семантической корректности сгенерированных при помощи LLM TLA+ спецификаций", 14, True, 120),
    ):
        p = r.d.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.CENTER, False, after)
        set_font(p.add_run(text), size, bold)
    for text in ("Выполнил: ______________________ (ФИО, группа)", "Проверил: ______________________"):
        p = r.d.add_paragraph()
        fmt(p, WD_ALIGN_PARAGRAPH.RIGHT, False, 8)
        set_font(p.add_run(text))
    p = r.d.add_paragraph()
    fmt(p, WD_ALIGN_PARAGRAPH.CENTER, False, 0)
    p.paragraph_format.space_before = Pt(120)
    set_font(p.add_run("2026"))
    r.page_break()

    # --- введение
    r.heading("Введение")
    r.para("Целью работы является оценка того, насколько корректно (в том числе семантически) большая языковая модель "
           "(LLM) способна написать TLA+ спецификацию по текстовому описанию системы. Для этого модель итеративно "
           "исправляет спецификацию по логам синтаксического анализатора SANY и проверяющей модель программы TLC, "
           "после чего полученные спецификации сравниваются с эталонными (Gold) спецификациями.")
    r.para("Использованная модель: DeepSeek-V4-Pro-0813 (карточка на Hugging Face: deepseek-ai/DeepSeek-V4-Pro-0813, "
           "официальный релиз DeepSeek-V4-Pro; модель типа Mixture-of-Experts). Модель вызывалась через "
           "OpenAI-совместимый API агрегатора LiteRouter (https://api.literouter.com/v1) под идентификатором "
           "deepseek-v4-pro-0813:free (бесплатный вариант той же модели). Параметры генерации не переопределялись "
           "(значения по умолчанию провайдера: temperature = 1, top_p = 1).")
    r.para("Инструменты проверки: tla2tools.jar, SANY (TLA+ parser) и TLC2 Version 2.19 (08 August 2024), Java 21. "
           "Для воспроизводимости весь процесс автоматизирован скриптами; промпты, ответы модели, версии "
           "спецификаций и полные логи SANY и TLC сохранены и опубликованы в репозитории " + REPO_URL + ".")

    # --- выбранные задачи
    r.heading("1. Выбранные задачи")
    r.para("Задачи взяты из бенчмарка " + BENCH + " (gold-tier: спецификации, которые проходят и SANY, и TLC и "
           "имеют .cfg). Уровень сложности определён полем complexity манифеста: basic соответствует «лёгкому» уровню, "
           "intermediate – «среднему». Для каждой задачи собран набор данных: текстовое описание (поле "
           "desc_declarative_gpt), Gold спецификация и .cfg файл. В датасете файлы переименованы из "
           "<spec_id>_<Имя> в <Имя>, чтобы имя файла совпадало с именем модуля.")
    rows = []
    for i, (t, lvl) in enumerate(TASKS, 1):
        _, _, _, src = data[t]
        rows.append([i, TITLES[t], lvl, src.get("spec_id", "")])
    r.table(["№", "Задача", "Уровень", "spec_id"], rows, [1, 10.5, 4, 2])
    for i, (t, _) in enumerate(TASKS, 1):
        _, _, _, src = data[t]
        r.para(TITLES[t].split(" (")[0] + ":", indent=False)
        r.bullet("Gold спецификация (.tla): " + src["tla"])
        r.bullet("файл конфигурации (.cfg): " + src["cfg"])
        r.bullet("манифест (текстовые описания задач): " + src["manifest"])
        r.bullet("исходное происхождение: " + src["origin"])
        r.bullet("копия в рабочем репозитории: " + REPO_URL + "/dataset/" + t)

    # --- методика
    r.heading("2. Методика эксперимента")
    r.para("Для каждой задачи выполнялся цикл (не более 10 итераций, итерация – одна отправка промпта с контекстом "
           "и получение ответа): 1) отправка промпта; 2) из ответа берётся последний блок кода ```tla с целым модулем "
           "и сохраняется без правок; 3) запуск SANY (java -cp tla2tools.jar tla2sany.SANY <Модуль>.tla); 4) если SANY "
           "прошёл, запуск TLC (java -cp tla2tools.jar tlc2.TLC -config <Модуль>.cfg -workers auto <Модуль>.tla, "
           "таймаут 600 с); 5) полный лог ошибки отправляется модели в следующем промпте. Цикл останавливается, когда "
           "прошли и SANY, и TLC, либо после 10 итераций.")
    r.para("Шаблоны промптов (tools/prompts/ в репозитории): первый промпт (генерация) содержит описание, .cfg и "
           "требования; промпт для ошибки SANY содержит текущую спецификацию и полный лог SANY; промпт для ошибки TLC "
           "содержит текущую спецификацию, .cfg и полный лог TLC. Дополнительные подсказки модели не давались, "
           "Gold спецификация модели не показывалась ни в каком виде (кроме .cfg).")
    r.para("Типы ошибок классифицировались так. SANY: синтаксис, неопределённое имя, выдуманный оператор или модуль, "
           "неверный уровень выражения, неверное число аргументов, имя модуля не совпало с файлом. TLC: deadlock, "
           "нарушение инварианта, ошибка конфигурации, нарушение temporal-свойства, ошибка вычисления, timeout. Тип "
           "определялся автоматически по тексту лога и затем проверялся вручную.")
    r.para("Семантическая проверка (п. 4 задания) выполнялась уже после генерации: сравнение числа состояний (TLC с "
           "-workers 1, чтобы глубина была детерминированной), проверка refinement «сгенерированная ⇒ Gold» через "
           "Gold == INSTANCE SpecGold WITH ..., GoldSpec == Gold!Spec и PROPERTY GoldSpec в .cfg, проверка инвариантов "
           "и свойств Gold на поведениях сгенерированной спецификации, а также обратный refinement «Gold ⇒ "
           "сгенерированная». Отображение переменных Gold в переменные модели подбиралось вручную.")

    # --- п.3 результаты генерации
    r.heading("3. Результаты генерации спецификаций")
    r.para("Для генерации спецификаций при помощи LLM использовался следующий подход:", indent=False)
    for t, _ in TASKS:
        summary, rows_, sem, _ = data[t]
        r.heading(TITLES[t].split(" (")[0], 2)
        sany_err, tlc_err = ERRORS_SANY_TLC[t]
        total = summary["total_iterations"]
        r.box([
            ("Название задачи: ", TITLES[t]),
            ("А) ", PROMPT_INFO),
            ("Б) Во время генерации корректной спецификации LLM совершала следующие типы ошибок:\n", ""),
            ("– для SANY: ", sany_err),
            ("– для TLC: ", tlc_err),
            ("В) Для данной задачи были вычислены следующие метрики:\n", ""),
            ("– SANY прошёл проверку на итерации ", str(summary["sany_pass_iter"])),
            ("– TLC прошёл проверку на итерации ", str(summary["tlc_pass_iter"])),
            ("– Всего потребовалось ", f"{total} {'итерация' if total == 1 else 'итерации' if total < 5 else 'итераций'}"),
        ])
        r.para("Журнал итераций:", indent=False)
        r.table(["№", "SANY", "TLC", "Тип ошибки", "Что сломано"],
                [[x["n"], x["sany"], x["tlc"], x["type"], x["what"]] for x in rows_],
                [0.9, 1.5, 1.5, 4, 8.8])

    r.heading("Сводка по генерации", 2)
    rows = []
    for t, lvl in TASKS:
        s = data[t][0]
        rows.append([t.split("_", 2)[2], lvl.split(" ")[0], s["sany_pass_iter"], s["tlc_pass_iter"], s["total_iterations"]])
    r.table(["Задача", "Уровень", "SANY прошёл на итерации", "TLC прошёл на итерации", "Всего итераций"], rows,
            [5.5, 2.5, 3.2, 3.2, 2.8])
    r.para("Все четыре задачи были решены (SANY и TLC пройдены) за 1–5 итераций из допустимых 10; задач, в которых "
           "модель исчерпала лимит, нет, поэтому разбор причин неудачи не требуется. Лёгкие задачи потребовали 1 и 2 "
           "итерации, средние – 3 и 5. Ошибки SANY встретились только в средних задачах (выдуманный оператор, "
           "конфликт и неопределённость имён), ошибки TLC – в трёх из четырёх (вычисление, liveness, deadlock).")

    # --- п.4
    r.heading("4. Проверка семантической корректности")
    for t, _ in TASKS:
        summary, _, sem, _ = data[t]
        g, s = sem["gold"], sem["generated"]
        r.heading(TITLES[t].split(" (")[0], 2)
        r.table(["Спецификация", "Distinct States", "Total States (generated)", "Max Depth"],
                [["Gold", g["distinct_states"], g["states_generated"], g["depth"]],
                 [f"Сгенерированная (итерация {summary['tlc_pass_iter']})", s["distinct_states"],
                  s["states_generated"], s["depth"]]], [6, 3, 4, 2.5])
        def label(c):
            s = c["check"]
            if s.startswith("reverse refinement"):
                return "Обратный refinement: Gold ⇒ сгенерированная"
            if s.startswith("refinement"):
                return "Refinement: сгенерированная ⇒ Gold (PROPERTY GoldSpec)"
            kind = "Инвариант" if s.startswith("invariant") else "Свойство"
            return f"{kind} {s.split()[1]} на поведениях сгенерированной спецификации"

        checks = [[label(c), "выполняется" if c["status"] == "pass" else "НАРУШЕНО (контрпример TLC)"]
                  for c in sem["checks"]]
        r.table(["Проверка TLC", "Результат"], checks, [11, 5.5])
        a, b = SEM[t]
        r.box([("Название задачи: ", TITLES[t]),
               ("А) Анализ состояний сгенерированной и Gold спецификации показал: ", a),
               ("Б) При сравнении двух спецификаций было выяснено: ", b)])

    # --- п.5
    r.heading("5. Выводы")
    r.para("Формально модель справилась со всеми четырьмя задачами: каждая итоговая спецификация проходит SANY и TLC "
           "с заданной конфигурацией, максимум за 5 итераций. Однако семантическая проверка показывает, что прохождение "
           "SANY и TLC не гарантирует правильность по смыслу.")
    r.table(["Задача", "Refinement ⇒ Gold", "Gold ⇒ сгенер.", "Оценка"],
            [["AsynchInterface", "выполняется", "нарушен (начальные состояния)", "корректное сужение Gold"],
             ["TCommit", "нарушен", "нарушен", "расходится с Gold: неверное условие commit/abort"],
             ["SimpleAllocator", "нарушен", "нарушен", "ослаблена, не эквивалентна Gold"],
             ["SyncTerminationDetection", "выполняется", "нарушен (начальное состояние, соседи)",
              "корректное сужение Gold с лишней переменной tick"]], [3.8, 3.4, 4.3, 5.0])
    r.para("Итого: две из четырёх спецификаций (AsynchInterface и SyncTerminationDetection) семантически корректны в "
           "смысле refinement, но уже Gold и не эквивалентны ему; две (TCommit и SimpleAllocator) расходятся с Gold по "
           "существу. Ни одна спецификация не эквивалентна Gold: обратный refinement нарушен во всех случаях. "
           "Наибольшее расхождение у SimpleAllocator: пространство состояний в девять раз меньше, чем у Gold.")
    r.para("Возможные причины ошибок и расхождений:", indent=False)
    for text in (
        "Неполнота естественного языка. Описание передаёт общий смысл, но не точные условия действий: в TCommit нет "
        "предиката canCommit, в AsynchInterface нет начальных значений рукопожатия, названия liveness-свойств "
        "SimpleAllocator даны только именами в .cfg. Модель заполняет пробелы собственными допущениями.",
        "Слабые проверки в .cfg. Для TCommit TLC проверяет только TCTypeOK и TCConsistent, и спецификация с неверным "
        "условием commit их проходит. Критерий «TLC пройден» не отражает все требования Gold.",
        "Оптимизация под проверяющий инструмент вместо смысла. При liveness-ошибках в SimpleAllocator модель ослабила "
        "спецификацию и переопределила свойства (ClientsWillObtain стало почти тривиальным), а в "
        "SyncTerminationDetection вылечила deadlock искусственной переменной tick. Это поведение, при котором "
        "инструмент перестаёт ругаться, но смысл теряется.",
        "Сложность temporal-свойств и справедливости (fairness). Для SimpleAllocator нужно согласовать условия "
        "справедливости с точными guard-условиями действий; counterexample TLC показывал голодание клиентов, но "
        "модель на итерациях 2–4 меняла отдельные действия и в итоге ослабила спецификацию вместо того, чтобы "
        "восстановить поведение, описанное в тексте.",
        "Малая представленность TLA+ в обучающих данных и особенности синтаксиса: Union {...} вместо UNION, "
        "конфликт имени вспомогательного оператора Next(i) с Next, использование i' без определения; такие ошибки "
        "исправлялись по логу SANY за одну итерацию, т. е. синтаксис модели доступен, но не отработан.",
        "Дословная интерпретация формулировок: слово «ring» в SyncTerminationDetection модель восприняла как "
        "ограничение «будить можно только соседа», хотя в Gold любой активный узел может будить любой.",
    ):
        r.bullet(text)
    r.para("Ограничения эксперимента: по одному запуску на задачу при температуре 1 (результаты недетерминированы); "
           "использовалась бесплатная версия модели через агрегатор; всего четыре задачи; отображение переменных для "
           "refinement подбиралось вручную; описания задач сгенерированы автоматически (desc_declarative_gpt), "
           "а не написаны человеком.")
    r.heading("Приложение. Материалы эксперимента")
    r.para("Репозиторий: " + REPO_URL + ". Структура: dataset/ (описания, .cfg, Gold), tools/ (скрипты и шаблоны "
           "промптов), runs/" + MODEL_DIR + "/<задача>/ (prompt_N.md, response_N.md, spec_iterN.tla, sany_N.log, "
           "tlc_N.log, run.log, results.md, summary.json, transcript.json и semantic/ с обёртками и логами "
           "сравнения с Gold).")

    out = ROOT / "report"
    out.mkdir(exist_ok=True)
    path = out / "Отчет_вариант1.docx"
    r.d.save(path)
    print("saved", path)


if __name__ == "__main__":
    main()

