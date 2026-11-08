You are an expert in TLA+ formal specification.

Task: write a complete TLA+ specification for the system described below.

# System description
{DESCRIPTION}

# TLC configuration file
The specification will be checked with SANY and then with TLC using this
exact configuration file. Your specification must be compatible with it
(use the same names for constants, variables, operators, invariants and
properties it refers to):

{CFG_CONTENT}

# Requirements
- The module name must be: {MODULE_NAME}
- The specification must pass SANY (parsing) and TLC (model checking) with
  the configuration above without errors.
- Think step by step briefly first, then output the final specification
  as a single ```tla code block containing the whole module and nothing else
  inside that block.
