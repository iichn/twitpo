---- MODULE CompareRev ----
EXTENDS SpecGold
Gen == INSTANCE SyncTerminationDetection WITH
    N <- N,
    active <- [i \in 1..N |-> active[i - 1]],
    detected <- terminationDetected,
    tick <- FALSE
GenSpec == Gen!Spec
====
