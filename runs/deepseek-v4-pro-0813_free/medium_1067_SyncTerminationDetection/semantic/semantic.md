# Семантическое сравнение: medium_1067_SyncTerminationDetection

## а) Размер пространства состояний

| Спецификация | Distinct states | States generated | Max depth |
|---|---|---|---|
| Gold | 129 | 3722 | 1 |
| Сгенерированная (итерация 3) | 258 | 1860 | 2 |

## б–г) Проверки через TLC

| Проверка | Результат |
|---|---|
| refinement: generated => Gold | pass |
| invariant Gold!TypeOK on generated behaviors | pass |
| invariant Gold!TDCorrect on generated behaviors | pass |
| property Gold!Quiescence on generated behaviors | pass |
| property Gold!Liveness on generated behaviors | pass |
| reverse refinement: Gold => generated | fail: Error: Property line 16, col 8 to line 16, col 23 of module SyncTerminationDetection is violated by the initial state: |
