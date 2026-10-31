# Семантическое сравнение: medium_1000_SimpleAllocator

## а) Размер пространства состояний

| Спецификация | Distinct states | States generated | Max depth |
|---|---|---|---|
| Gold | 400 | 1633 | 6 |
| Сгенерированная (итерация 5) | 43 | 94 | 5 |

## б–г) Проверки через TLC

| Проверка | Результат |
|---|---|
| refinement: generated => Gold | fail: Error: Action property line 72, col 14 to line 72, col 26 of module SpecGold is violated. |
| invariant Gold!TypeInvariant on generated behaviors | pass |
| invariant Gold!ResourceMutex on generated behaviors | pass |
| property Gold!ClientsWillReturn on generated behaviors | pass |
| property Gold!ClientsWillObtain on generated behaviors | fail: Error: Temporal properties were violated. |
| property Gold!InfOftenSatisfied on generated behaviors | pass |
| reverse refinement: Gold => generated | fail: Error: Action property line 41, col 8 to line 41, col 20 of module SimpleAllocator is violated. |
