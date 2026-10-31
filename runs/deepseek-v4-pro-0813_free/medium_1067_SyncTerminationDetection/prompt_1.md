You are an expert in TLA+ formal specification.

Task: write a complete TLA+ specification for the system described below.

# System description
This module specifies an abstract termination-detection problem for a ring with synchronous communication. It models a set of nodes indexed by Node, where each node may be active or inactive, and a boolean flag records whether global termination has been detected. The actions allow active nodes to terminate, active nodes to wake up other nodes, and a separate detection step to set the detection flag when all nodes are inactive; the specification also states a fairness condition on the detection action and defines correctness, quiescence, and liveness-style temporal properties.

# TLC configuration file
The specification will be checked with SANY and then with TLC using this
exact configuration file. Your specification must be compatible with it
(use the same names for constants, variables, operators, invariants and
properties it refers to):

CONSTANTS
    N = 7

SPECIFICATION 
    Spec

INVARIANTS
    TypeOK
    TDCorrect

PROPERTIES
    Quiescence
    Liveness

# Requirements
- The module name must be: SyncTerminationDetection
- The specification must pass SANY (parsing) and TLC (model checking) with
  the configuration above without errors.
- Think step by step briefly first, then output the final specification
  as a single ```tla code block containing the whole module and nothing else
  inside that block.
