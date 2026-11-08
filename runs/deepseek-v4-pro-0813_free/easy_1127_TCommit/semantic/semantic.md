# Семантическое сравнение: easy_1127_TCommit

## а) Размер пространства состояний

| Спецификация | Distinct states | States generated | Max depth |
|---|---|---|---|
| Gold | 34 | 94 | 7 |
| Сгенерированная (итерация 2) | 46 | 97 | 7 |

## б–г) Проверки через TLC

| Проверка | Результат |
|---|---|
| refinement: generated => Gold | fail: Error: Action property line 46, col 21 to line 46, col 38 of module SpecGold is violated. |
| invariant Gold!TCTypeOK on generated behaviors | pass |
| invariant Gold!TCConsistent on generated behaviors | pass |
| reverse refinement: Gold => generated | fail: Error: Action property line 26, col 19 to line 26, col 34 of module TCommit is violated. |
