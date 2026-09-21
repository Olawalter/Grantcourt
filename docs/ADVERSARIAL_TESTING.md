# Adversarial testing

The attacks the suite runs, where each one is tested, and the safety property
each one pins. Every test asserts the final state and what it does to money.

Files: `tests/direct/test_grantcourt_adversarial.py` (hostile evidence, forged
leaders, disagreeing validators), `tests/direct/test_grantcourt_hardening.py`
(boundaries, malformed input, lifecycle), `tests/direct/test_grantcourt.py`
(every catalogue case), `fixtures/adversarial_submissions.json` (AD01-AD09).

## Malicious submission content

| Attack | Case or test | Expected | Property |
|---|---|---|---|
| prompt injection in a README | AD01 | FAIL / MANIPULATION, panel not asked, bond forfeited | evidence cannot instruct the evaluator |
| prompt injection in documentation | AD02 | same | every applicant item is scanned, not only the primary |
| prompt injection hidden in webpage markup | AD03 | same | markup a browser hides is still text |
| instruction injected through a screenshot's text | AD04 | same | a transcript is evidence and is scanned |
| hidden zero-width characters | AD05 | INSUFFICIENT_EVIDENCE / HIDDEN_TEXT | text a reader cannot see is not read |
| an injection phrase quoted as data | HK01 | PASS, no markers | the negative control: quoting is not manipulation |
| a hostile program reference | `test_a_malicious_reference_source_is_withheld...` | reference withheld, applicant unaffected | the owner's material cannot sink an applicant |
| an attempt to redefine the rubric without marker phrases | AD09, `test_evidence_cannot_redefine_the_rubric` | judged against the stored criteria | the rubric is the constitution |

## Forged and reused evidence

| Attack | Case or test | Expected | Property |
|---|---|---|---|
| fake deployment evidence | AD08 | FAIL / CLAIM_CONTRADICTED, critical | a claim the evidence contradicts blocks the reward |
| evidence that passed for another applicant | `test_evidence_that_passed_for_another_applicant...` | FAIL / DUPLICATE_EVIDENCE, bond forfeited | no cross-submission contamination |
| the program's own reference passed off as work | AD07 | FAIL / DUPLICATE_EVIDENCE | reference bytes are not the applicant's |
| evidence filed early by a copier but never passed | `test_evidence_filed_but_not_passed...` | not held against the author | a copy cannot block the author |
| evidence altered after filing | `test_evidence_altered_after_filing...`, `test_a_changed_primary...` | HASH_MISMATCH, never read | the committed bytes are the evidence |
| one item repeated to count twice | hardening: "evidence must not repeat" | refused, bond returned | no evidence amplification |
| an applicant taking down evidence to appeal | `test_an_applicant_cannot_take_down...` | appeal refused | an appeal never judges less |

## Evaluator manipulation (the model)

| Attack | Test | Expected |
|---|---|---|
| a criterion claimed MET without evidence | `test_a_criterion_claimed_met_without_evidence...` | EVIDENCE_INSUFFICIENT, no reward |
| MET quoting an item of the wrong category, or a reference | hardening: category and reference tests | not MET |
| an unknown enum | `test_an_unknown_enum_is_undecided` | undecided |
| a model-stated score of 150, a status and an amount | `test_a_model_stating_a_score_or_an_amount...` | ignored; score, band and reward from code |
| an omitted required criterion | `test_an_omitted_required_criterion...` | INSUFFICIENT_EVIDENCE |
| duplicate criterion answers | `test_duplicate_criterion_answers...` | one finding |
| excessively long reasoning | `test_an_oversized_note_is_cut...` | cut to 200 characters |
| malformed JSON | `test_undecided_and_failed_readings_never_pass` | INCONCLUSIVE / MODEL_OUTPUT_INVALID |
| SIMILAR on shared subject matter | `test_quotes_sharing_a_few_words...` | not similar |

## Leader-result manipulation

`test_a_malformed_or_forged_leader_payload_is_refused` hands the captured
validator 30 forged payloads through `direct_vm.run_validator`: a changed
schema, round, clock, policy hash or evidence commitment; a fabricated
applicant mark, marker or code reason; an added `overall_score` or
`reward_atto`; rows claiming unread evidence was read; a dropped, reordered or
duplicated finding; an unknown state; a finding claimed by code; an oversized
note; an invented quote; a SIMILAR or CONTRADICTED without its support; an
extra field. Every one is refused. Further tests show:

- validators disagreeing on a required criterion do not ratify;
- a required criterion's state is compared even when the status matches;
- evidence changing between the leader's and the validator's attempt is a
  disagreement;
- a leader claiming unavailable evidence was read, hiding a marker, or
  misreporting a withheld reference is outvoted;
- notes, quote choice and optional criteria inside one band are not compared;
  a score crossing a band is;
- a leader error is ratified only by the same deterministic error or by a
  transient meeting a transient; a model failure never.

## Replay, oversized input, source substitution, policy tampering

| Attack | Test | Expected |
|---|---|---|
| a second evaluation, a second appeal, a second finalization, a second withdrawal | `test_nothing_happens_twice...`, `test_appeals_are_bounded` | refused |
| oversized strings and arrays | hardening: 81-character name, 1201-character description, 7 items, 6 claims | refused, bond returned |
| an item over 12,000 bytes | `test_an_oversized_primary...` | TOO_LARGE, not read |
| source substitution after filing | altered-evidence tests | HASH_MISMATCH |
| a policy version mismatch | hardening: `definition_hash` of zeros | refused, bond returned |
| rewriting a constitution | `test_a_constitution_is_never_rewritten...` | impossible; only a higher version by the same owner supersedes |
| URLs to localhost, IP literals, http, dot-segments | constitution and application tests | refused |

## Safety properties

| Property | Where it is pinned |
|---|---|
| No unauthorized evaluation | only the applicant or owner requests; only the applicant appeals; only the grantee files milestones |
| No silent policy mutation | constitutions are never rewritten; records carry the hash and version |
| No reward from unresolved uncertainty | `test_an_inconclusive_result_is_never_rewardable` and every undecided reading |
| No arbitrary score | scores are integers 0-100 from weights and states; band boundary tests at 60, 70, 80, 90, 100 |
| No evidence amplification | repeated items refused |
| No appeal loop | one appeal; a second is refused |
| No cross-submission contamination | a round reads only its application's items and the program's references |
| No finalized-state mutation | every write refused after finalization; receipt and record unchanged |
| No model-controlled arithmetic | model-stated scores and amounts ignored; forged payload fields refused |

## Mutation check

`python scripts/mutation_check.py --jobs 3` breaks one guard at a time in a
scratch copy and runs the whole suite against it, after an accept-control that
the unmodified copy passes. The result is recorded in
`deploy/mutation_sweep.txt`.
