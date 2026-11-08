---- MODULE CompareRev ----
EXTENDS SpecGold
Gen == INSTANCE SimpleAllocator WITH
    Clients <- Clients,
    Resources <- Resources,
    requested <- unsat,
    allocated <- alloc
GenSpec == Gen!SimpleAllocator
====
