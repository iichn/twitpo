You are an expert in TLA+ formal specification.

Task: write a complete TLA+ specification for the system described below.

# System description
This module specifies a simple resource allocator for a finite set of resources and a set of clients. Clients issue requests only when they currently hold no resources and have no outstanding unsatisfied request; requests may then be partially fulfilled over time, and clients may return held resources even before a request is completely satisfied. The specification defines two temporal system specifications with different fairness assumptions, and proves safety and liveness properties such as type correctness, mutual exclusion of resource ownership, eventual return, eventual obtainment, and infinitely often having no unsatisfied requests; it also includes a symmetry expression and a concrete counterexample value structure.

# TLC configuration file
The specification will be checked with SANY and then with TLC using this
exact configuration file. Your specification must be compatible with it
(use the same names for constants, variables, operators, invariants and
properties it refers to):

CONSTANTS
  Clients = {c1,c2,c3}
  Resources = {r1,r2}

SPECIFICATION
  SimpleAllocator

\** DOES NOT WORK FOR LIVENESS !
\** SYMMETRY Symmetry

INVARIANTS
  TypeInvariant ResourceMutex

PROPERTIES
  ClientsWillReturn ClientsWillObtain InfOftenSatisfied

# Requirements
- The module name must be: SimpleAllocator
- The specification must pass SANY (parsing) and TLC (model checking) with
  the configuration above without errors.
- Think step by step briefly first, then output the final specification
  as a single ```tla code block containing the whole module and nothing else
  inside that block.
