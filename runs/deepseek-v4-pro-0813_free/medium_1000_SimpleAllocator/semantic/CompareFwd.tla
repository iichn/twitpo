---- MODULE CompareFwd ----
EXTENDS SimpleAllocator
Gold == INSTANCE SpecGold WITH
    Clients <- Clients,
    Resources <- Resources,
    unsat <- requested,
    alloc <- allocated
GoldSpec == Gold!SimpleAllocator
Gold_TypeInvariant == Gold!TypeInvariant
Gold_ResourceMutex == Gold!ResourceMutex
Gold_ClientsWillReturn == Gold!ClientsWillReturn
Gold_ClientsWillObtain == Gold!ClientsWillObtain
Gold_InfOftenSatisfied == Gold!InfOftenSatisfied
====
