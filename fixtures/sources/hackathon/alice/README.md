# Clauseguard

Applicant wallet: 0x2181588581f943be374fbde775cd83c4c4b2bbcc
Built for the GenLayer Judgment Hackathon.

Clauseguard flags unfair clauses in freelance contracts. A freelancer pastes a
contract clause; an Intelligent Contract asks a validator panel whether the
clause shifts unreasonable risk onto the freelancer, and records the verdict
with the reasons the panel agreed on.

## Why this needs GenLayer

Whether a clause is unfair is a judgment about meaning, not a rule a regular
contract can compute. Each validator reads the clause with its own model and
the validators must agree on the verdict field before it is stored.

## Safety

Clause text is treated as data. Clause text such as "ignore previous
instructions" is quoted back as part of the clause and never followed.

## Running it

Run the direct tests with pytest, then deploy with scripts/deploy.py. The
deployment record and the test report are linked from this repository.
