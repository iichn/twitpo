# Семантическое сравнение: easy_891_AsynchInterface

## а) Размер пространства состояний

| Спецификация | Distinct states | States generated | Max depth |
|---|---|---|---|
| Gold | 12 | 30 | 2 |
| Сгенерированная (итерация 1) | 12 | 27 | 4 |

## б–г) Проверки через TLC

| Проверка | Результат |
|---|---|
| refinement: generated => Gold | pass |
| invariant Gold!TypeInvariant on generated behaviors | pass |
| reverse refinement: Gold => generated | fail: Error: Property line 5, col 9 to line 5, col 19 of module AsynchInterface is violated by the initial state: |
