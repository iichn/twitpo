---- MODULE TCommit ----
CONSTANT RM
VARIABLE rmState

TCTypeOK == \A rm \in RM : rmState[rm] \in {"working", "prepared", "committed", "aborted"}

Init == rmState = [rm \in RM |-> "working"]

Prepare(rm) == /\ rmState[rm] = "working"
               /\ rmState' = [rmState EXCEPT ![rm] = "prepared"]

Commit(rm) == /\ rmState[rm] = "prepared"
              /\ \A other \in RM \ {rm} : rmState[other] /= "aborted"
              /\ rmState' = [rmState EXCEPT ![rm] = "committed"]

Abort(rm) == /\ rmState[rm] = "prepared"
             /\ \A other \in RM \ {rm} : rmState[other] /= "committed"
             /\ rmState' = [rmState EXCEPT ![rm] = "aborted"]

Decide(rm) == Commit(rm) \/ Abort(rm)

Next == \E rm \in RM : Prepare(rm) \/ Decide(rm)

TCConsistent == \A rm1, rm2 \in RM : ~ (rmState[rm1] = "committed" /\ rmState[rm2] = "aborted")

TCSpec == Init /\ [][Next]_rmState
====
