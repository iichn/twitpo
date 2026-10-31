You are an expert in TLA+ formal specification.

Task: write a complete TLA+ specification for the system described below.

# System description
This module specifies a simple asynchronous sender-receiver interface using a handshake between the variables rdy and ack, with val carrying data from the set Data. The sender may perform Send only when rdy = ack, at which point it chooses a new value for val and toggles rdy; the receiver may perform Rcv only when rdy # ack, at which point it toggles ack and leaves val and rdy unchanged. The specification defines an initial state, a next-state relation, and a temporal specification requiring all behaviors to start in Init and then follow Next with stuttering allowed; it also states a theorem that Spec implies the invariant TypeInvariant always holds.

# TLC configuration file
The specification will be checked with SANY and then with TLC using this
exact configuration file. Your specification must be compatible with it
(use the same names for constants, variables, operators, invariants and
properties it refers to):

(***************************************************************************)
(* This is a configuration file for testing the specification Spec of      *)
(* module AsynchInterface.  It checks that TypeInvariant is an invariant   *)
(* of Spec.                                                                *)
(***************************************************************************)

SPECIFICATION Spec
   \* This statement tells TLC that Spec is the specification to be
   \* checked.

INVARIANT TypeInvariant
   \* This statement tells TLC to check that TypeInvariant is an
   \* invariant of the specification.

(***************************************************************************)
(* TLC requires that every declared constant in the specification be       *)
(* assigned a value by a CONSTANT statement in the configuration file.     *)
(***************************************************************************)
CONSTANT
  Data = {d1, d2, d3}
    \* This assigns to the declared constant Data the set consisting of
    \* the three unspecified values d1, d2, d3.

# Requirements
- The module name must be: AsynchInterface
- The specification must pass SANY (parsing) and TLC (model checking) with
  the configuration above without errors.
- Think step by step briefly first, then output the final specification
  as a single ```tla code block containing the whole module and nothing else
  inside that block.
