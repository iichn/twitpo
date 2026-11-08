---- MODULE CompareRev ----
EXTENDS SpecGold
Gen == INSTANCE AsynchInterface WITH
    Data <- Data,
    val <- val,
    rdy <- (rdy = 1),
    ack <- (ack = 1)
GenSpec == Gen!Spec
====
