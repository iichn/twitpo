---- MODULE CompareFwd ----
EXTENDS AsynchInterface
Gold == INSTANCE SpecGold WITH
    Data <- Data,
    val <- val,
    rdy <- IF rdy THEN 1 ELSE 0,
    ack <- IF ack THEN 1 ELSE 0
GoldSpec == Gold!Spec
Gold_TypeInvariant == Gold!TypeInvariant
====
