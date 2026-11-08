You are an expert in TLA+ formal specification.

Task: write a complete TLA+ specification for the system described below.

# System description
This specification models the Two-Phase Commit (2PC) protocol for distributed transactions, focusing on the behavior of resource managers (RMs) as they transition through various states: working, prepared, committed, and aborted. The model defines the possible actions each RM can take (Prepare and Decide), and specifies the protocol's next-state relation as the disjunction of these actions for all RMs. The specification asserts type correctness and consistency invariants, ensuring that no two RMs can reach conflicting decisions (i.e., one committed and one aborted), and verifies these invariants as properties of the protocol. The model does not explicitly include faults or failures beyond the abort/commit logic, and does not model a coordinator or message passing.

# TLC configuration file
The specification will be checked with SANY and then with TLC using this
exact configuration file. Your specification must be compatible with it
(use the same names for constants, variables, operators, invariants and
properties it refers to):

CONSTANT RM = {r1, r2, r3}
INVARIANTS TCTypeOK TCConsistent
SPECIFICATION TCSpec
CHECK_DEADLOCK FALSE

# Requirements
- The module name must be: TCommit
- The specification must pass SANY (parsing) and TLC (model checking) with
  the configuration above without errors.
- Think step by step briefly first, then output the final specification
  as a single ```tla code block containing the whole module and nothing else
  inside that block.
