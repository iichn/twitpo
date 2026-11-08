---- MODULE CompareFwd ----
EXTENDS TCommit
Gold == INSTANCE SpecGold WITH
    RM <- RM,
    rmState <- rmState
GoldSpec == Gold!TCSpec
Gold_TCTypeOK == Gold!TCTypeOK
Gold_TCConsistent == Gold!TCConsistent
====
