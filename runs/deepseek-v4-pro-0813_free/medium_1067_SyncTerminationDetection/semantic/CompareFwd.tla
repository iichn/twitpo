---- MODULE CompareFwd ----
EXTENDS SyncTerminationDetection
Gold == INSTANCE SpecGold WITH
    N <- N,
    active <- [n \in 0..N-1 |-> active[n + 1]],
    terminationDetected <- detected
GoldSpec == Gold!Spec
Gold_TypeOK == Gold!TypeOK
Gold_TDCorrect == Gold!TDCorrect
Gold_Quiescence == Gold!Quiescence
Gold_Liveness == Gold!Liveness
====
