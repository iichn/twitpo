# Dataset (variant 1): TLA+ generation with LLM

Source: https://github.com/LUC-AI4FM/tla_benchmark/tree/dataset-release/dataset_release
(`basic` = easy, `intermediate` = medium; only gold-tier specs with a `.cfg`).

| Folder | spec_id | Level | Gold TLC: distinct / generated / depth |
|---|---|---|---|
| `easy_891_AsynchInterface` | 891 | easy | 12 / 30 / 2 |
| `easy_1127_TCommit` | 1127 | easy | 34 / 94 / 7 |
| `medium_1000_SimpleAllocator` | 1000 | medium | 400 / 1633 / 6 |
| `medium_1067_SyncTerminationDetection` | 1067 | medium | 129 / 3722 / 1 |

Each folder contains:
- `description.txt` - the only text given to the LLM (`desc_declarative_gpt`);
- `<Module>.cfg` - TLC config (may be shown to the LLM);
- `gold/<Module>.tla` - gold spec (must NOT be shown to the LLM);
- `source.txt` - links to the original files.

Files are renamed from `<id>_<Name>` to `<Name>` so the file name matches the module name (required by SANY/TLC).

Run one iteration (SANY, then TLC; logs go to `<task>/iterations/iterNN/`):

```
python tools/check.py dataset/easy_891_AsynchInterface answer.tla 1
```
