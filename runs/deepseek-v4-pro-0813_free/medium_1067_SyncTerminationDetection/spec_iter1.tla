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
