---- MODULE CompareRev ----
EXTENDS SpecGold
Gen == INSTANCE TCommit WITH
    RM <- RM,
    rmState <- rmState
GenSpec == Gen!TCSpec
====
