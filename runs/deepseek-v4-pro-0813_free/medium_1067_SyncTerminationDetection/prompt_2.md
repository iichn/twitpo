The specification below failed SANY parsing.

# Current specification

```
---- MODULE SyncTerminationDetection ----
EXTENDS Integers

CONSTANT N

Node == 1..N

Next(i) == IF i = N THEN 1 ELSE i + 1

VARIABLES active, detected

vars == <<active, detected>>

Init ==
    /\ active \in [Node -> BOOLEAN]
    /\ detected = FALSE

Terminate ==
    /\ \E i \in Node : active[i]
    /\ ~detected
    /\ active' = [active EXCEPT ![i] = FALSE]
    /\ detected' = detected

WakeUp ==
    /\ \E i \in Node : active[i] /\ ~active[Next(i)]
    /\ ~detected
    /\ active' = [active EXCEPT ![Next(i)] = TRUE]
    /\ detected' = detected

Detect ==
    /\ \A i \in Node : ~active[i]
    /\ ~detected
    /\ detected' = TRUE
    /\ active' = active

Next == Terminate \/ WakeUp \/ Detect

Spec == Init /\ [][Next]_vars /\ WF_vars(Detect)

TypeOK ==
    /\ active \in [Node -> BOOLEAN]
    /\ detected \in BOOLEAN

TDCorrect ==
    detected => \A i \in Node : ~active[i]

Quiescence ==
    []( (\A i \in Node : ~active[i]) => []( \A i \in Node : ~active[i] ) )

Liveness ==
    (\A i \in Node : ~active[i]) ~> detected

====

```

# SANY log


****** SANY2 Version 2.1 created 24 February 2014

Parsing file E:\������� ����\ai project\testing_verification\runs\deepseek-v4-pro-0813_free\medium_1067_SyncTerminationDetection\work\SyncTerminationDetection.tla
Parsing file C:\Users\��������\AppData\Local\Temp\Integers.tla
Parsing file C:\Users\��������\AppData\Local\Temp\Naturals.tla
Semantic processing of module Naturals
Semantic processing of module Integers
Semantic processing of module SyncTerminationDetection
Semantic errors:

*** Errors: 5

line 21, col 35 to line 21, col 35 of module SyncTerminationDetection

Unknown operator: `i'.


line 27, col 40 to line 27, col 40 of module SyncTerminationDetection

Unknown operator: `i'.


line 36, col 1 to line 36, col 37 of module SyncTerminationDetection

Operator Next already defined or declared.


line 36, col 1 to line 36, col 37 of module SyncTerminationDetection

Multiply-defined symbol 'Next': this definition or declaration conflicts 
with the one at line 8, col 1 to line 8, col 37 of module SyncTerminationDetection.


line 38, col 20 to line 38, col 23 of module SyncTerminationDetection

The operator Next requires 1 arguments.





Provide the corrected, complete specification as a single ```tla code block.
