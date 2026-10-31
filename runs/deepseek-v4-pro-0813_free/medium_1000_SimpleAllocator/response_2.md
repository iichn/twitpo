```tla
-------------------------- MODULE SimpleAllocator --------------------------
EXTENDS Naturals, FiniteSets

CONSTANTS Clients, Resources

VARIABLES allocated, requested

vars == <<allocated, requested>>

TypeOK == /\ allocated \in [Clients -> SUBSET Resources]
          /\ requested \in [Clients -> SUBSET Resources]

Init == /\ allocated = [c \in Clients |-> {}]
        /\ requested = [c \in Clients |-> {}]

Request(c) ==
    /\ allocated[c] = {}
    /\ requested[c] = {}
    /\ \E S \in SUBSET Resources : S # {} /\ requested' = [requested EXCEPT ![c] = S]
    /\ UNCHANGED allocated

Allocate(c) ==
    \E r \in Resources :
        /\ r \in requested[c]
        /\ r \notin UNION {allocated[other] : other \in Clients}
        /\ allocated' = [allocated EXCEPT ![c] = allocated[c] \cup {r}]
        /\ requested' = [requested EXCEPT ![c] = requested[c] \ {r}]

Return(c) ==
    \E r \in Resources :
        /\ r \in allocated[c]
        /\ allocated' = [allocated EXCEPT ![c] = allocated[c] \ {r}]
        /\ requested' = [requested EXCEPT ![c] = requested[c] \cup {r}]

Next == \E c \in Clients : Request(c) \/ Allocate(c) \/ Return(c)

SimpleAllocator ==
    Init
    /\ [][Next]_vars
    /\ \A c \in Clients :
        /\ WF_vars(Request(c))
        /\ WF_vars(Return(c))
        /\ SF_vars(Allocate(c))

SimpleAllocatorWeak ==
    Init
    /\ [][Next]_vars
    /\ \A c \in Clients :
        /\ WF_vars(Request(c))
        /\ WF_vars(Return(c))
        /\ WF_vars(Allocate(c))

TypeInvariant == TypeOK

ResourceMutex ==
    \A c1,c2 \in Clients : c1 # c2 => allocated[c1] \cap allocated[c2] = {}

ClientsWillReturn ==
    \A c \in Clients : \A r \in Resources :
        (r \in allocated[c]) ~> (r \notin allocated[c])

ClientsWillObtain ==
    \A c \in Clients : (requested[c] # {}) ~> (requested[c] = {})

InfOftenSatisfied ==
    []<>(\A c \in Clients : requested[c] = {})

Symmetry ==
    {f \in [Clients \cup Resources -> Clients \cup Resources] :
        /\ \A c \in Clients : f[c] \in Clients
        /\ \A r \in Resources : f[r] \in Resources
        /\ \A x,y \in Clients \cup Resources : f[x] = f[y] => x = y}

=============================================================================
\* The following is a concrete counterexample value structure that can be
\* used to demonstrate a violation of a liveness property under weak fairness.
\* It is not part of the specification itself, but is included for reference.
\* 
\* CounterexampleState ==
\*   [ allocated |-> [c1 |-> {r1}, c2 |-> {r2}, c3 |-> {}],
\*     requested |-> [c1 |-> {}, c2 |-> {}, c3 |-> {r1,r2}] ]
=============================================================================
```