---- MODULE SyncTerminationDetection ----
EXTENDS Integers

CONSTANT N

Node == 1..N

NextNode(i) == IF i = N THEN 1 ELSE i + 1

VARIABLES active, detected, tick

vars == <<active, detected, tick>>

Init ==
    /\ active \in [Node -> BOOLEAN]
    /\ detected = FALSE
    /\ tick \in BOOLEAN

Terminate ==
    \E i \in Node :
        /\ active[i]
        /\ ~detected
        /\ active' = [active EXCEPT ![i] = FALSE]
        /\ detected' = detected
        /\ tick' = tick

WakeUp ==
    \E i \in Node :
        /\ active[i] /\ ~active[NextNode(i)]
        /\ ~detected
        /\ active' = [active EXCEPT ![NextNode(i)] = TRUE]
        /\ detected' = detected
        /\ tick' = tick

Detect ==
    /\ \A i \in Node : ~active[i]
    /\ ~detected
    /\ detected' = TRUE
    /\ active' = active
    /\ tick' = tick

Tick ==
    /\ tick' = ~tick
    /\ UNCHANGED <<active, detected>>

Next == Terminate \/ WakeUp \/ Detect \/ Tick

Spec == Init /\ [][Next]_vars /\ WF_vars(Detect)

TypeOK ==
    /\ active \in [Node -> BOOLEAN]
    /\ detected \in BOOLEAN
    /\ tick \in BOOLEAN

TDCorrect ==
    detected => \A i \in Node : ~active[i]

Quiescence ==
    []( (\A i \in Node : ~active[i]) => []( \A i \in Node : ~active[i] ) )

Liveness ==
    (\A i \in Node : ~active[i]) ~> detected

====
