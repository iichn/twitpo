The specification models each resource manager's state as a function from RM to a string. The initial state has all RMs working. The Prepare action moves an RM from working to prepared. The Commit and Abort actions move an RM from prepared to committed or aborted respectively, with preconditions that prevent conflicting decisions: an RM can commit only if no other RM has aborted, and can abort only if no other RM has committed. The next-state relation is the disjunction of Prepare, Commit, and Abort for all RMs. The type invariant ensures each RM is in a valid state, and the consistency invariant ensures no two RMs have conflicting decisions.

```tla
---- MODULE TCommit ----
CONSTANT RM
VARIABLE rmState

TCTypeOK == \A rm \in RM : rmState[rm] \in {"working", "prepared", "committed", "aborted"}

Init == \A rm \in RM : rmState[rm] = "working"

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
```