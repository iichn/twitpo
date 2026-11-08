# Набор задач

Выборка включает четыре задачи из [LUC-AI4FM/tla_benchmark](https://github.com/LUC-AI4FM/tla_benchmark/tree/dataset-release/dataset_release). Использованы спецификации уровня `gold-tier`, которые проходят SANY и TLC и имеют соответствующий `.cfg` файл. Уровень сложности взят из поля `complexity` манифеста: `basic` — лёгкий, `intermediate` — средний.

| Каталог | `spec_id` | Уровень | Gold: distinct / generated / depth |
|---|---:|---|---:|
| `easy_891_AsynchInterface` | 891 | лёгкий (`basic`) | 12 / 30 / 2 |
| `easy_1127_TCommit` | 1127 | лёгкий (`basic`) | 34 / 94 / 7 |
| `medium_1000_SimpleAllocator` | 1000 | средний (`intermediate`) | 400 / 1633 / 6 |
| `medium_1067_SyncTerminationDetection` | 1067 | средний (`intermediate`) | 129 / 3722 / 1 |

## Содержимое каталога задачи

Каждый каталог содержит:

- `description.txt` — естественно-языковое описание из поля `desc_declarative_gpt`; именно этот текст передавался модели.
- `<Module>.cfg` — конфигурация TLC.
- `gold/<Module>.tla` — эталонная спецификация; при генерации не передавалась модели.
- `source.txt` — ссылки на исходные `.tla` и `.cfg`, манифест и сведения о происхождении задачи.

Файлы Gold переименованы из `<spec_id>_<Module>.tla` в `<Module>.tla`, чтобы имя файла совпадало с именем модуля TLA+ и запуск SANY/TLC проходил без переименования на лету.

Запуск генерации выполняется из корня репозитория, например:

```powershell
python src/run_experiment.py dataset/easy_891_AsynchInterface
```
