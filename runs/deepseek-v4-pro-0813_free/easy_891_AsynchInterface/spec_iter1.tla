------------------------ MODULE AsynchInterface -------------------------
CONSTANT Data
VARIABLES rdy, ack, val

Init == rdy = FALSE /\ ack = FALSE /\ val \in Data

Send == rdy = ack /\ val' \in Data /\ rdy' = ~rdy /\ ack' = ack

Rcv == rdy # ack /\ ack' = ~ack /\ rdy' = rdy /\ val' = val

Next == Send \/ Rcv

Spec == Init /\ [][Next]_<<rdy, ack, val>>

TypeInvariant == rdy \in BOOLEAN /\ ack \in BOOLEAN /\ val \in Data

THEOREM Spec => []TypeInvariant

=============================================================================
