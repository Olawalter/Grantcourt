# The equivalence principle

Validators on GenLayer do not need to produce identical outputs to agree. The
equivalence principle is the rule an Intelligent Contract gives its validators
for deciding when two results count as the same result.

A strict rule requires the outputs to match exactly, which suits data that
every honest node reads identically. A comparative rule lets each validator
compute its own result and compare the fields that decide what happens, while
explanations and wording are allowed to differ.

Choosing the rule is a design decision: compare too much and honest validators
disagree over wording; compare too little and a dishonest leader can slip a
different decision past them.
