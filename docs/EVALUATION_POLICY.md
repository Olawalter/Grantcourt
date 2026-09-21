# Evaluation policy

What a program constitution contains, how an application is scored, and every
status and reason code in the order the contract applies them.

## The constitution

`create_program(constitution_json)` takes exactly these keys; a missing or
unknown key is refused.

| Key | Type and bound |
|---|---|
| `title`, `description`, `eligibility_policy` | text: 120, 1200, 600 characters; nothing addressed to the evaluator, no hidden characters |
| `program_type` | `HACKATHON`, `GRANT_MILESTONE` or `CONTRIBUTION` |
| `accepted_submission_types` | 1+ of `PROJECT`, `MILESTONE_DELIVERABLE`, `TUTORIAL`, `ARTICLE`, `TRANSLATION`, `INTEGRATION`, `DOCUMENTATION` |
| `allowed_evidence_categories` | 1+ of `REPOSITORY_README`, `SOURCE_FILE`, `DEPLOYMENT_RECORD`, `DOCUMENTATION`, `TEST_REPORT`, `TRANSACTION_RECORD`, `SCREENSHOT_TRANSCRIPT`, `ARTICLE`, `MILESTONE_REPORT`, `OTHER` |
| `required_evidence_categories` | a subset of the allowed categories every application must include |
| `criteria` | 1 to 8: `criterion_id` (lowercase identifier), `name`, `description`, `weight` 1-100, `required` true/false, `evidence_categories` (the categories that can pass it; empty means any applicant item) |
| `pass_threshold` | integer 1-100 |
| `reward_bands` | 1 to 4 `{label, min_score, reward_atto}`, highest first, rewards not rising, the lowest band starting at `pass_threshold`; empty for a grant |
| `milestones` | a grant's 1 to 6 `{milestone_id M1.., title, definition, tranche_atto}`; empty otherwise |
| `grantee` | a grant's lowercase wallet; empty otherwise |
| `originality_policy` | `SIMILAR_BLOCKS_REWARD` or `SIMILAR_RECORDED_ONLY` |
| `reference_sources` | up to 3 hash-bound `{url, sha256, label}` |
| `require_applicant_mark` | the primary item must contain the applicant's address |
| `opens_at`, `deadline` | `YYYY-MM-DDTHH:MM:SSZ`, the deadline in the future |
| `appeal_window_seconds`, `stall_window_seconds` | 60 s to 60 days |
| `per_applicant_limit` | 1 to 10 |
| `submission_bond_atto` | up to 10 GEN, as a decimal string |
| `evaluation_policy_version`, `supersedes` | 1-1000; empty or the program id this version replaces (same owner, higher version) |

The constitution is stored as canonical JSON with its sha256
(`get_program_definition_hash` returns the stored and a recomputed hash). An
application must pass that hash to `submit`; a different hash is refused as a
policy version mismatch. Every evaluation record and receipt carries the hash
and the policy version it was judged under.

## An example: the hackathon in the fixtures

| Criterion | Weight | Required | Evidence that can pass it |
|---|---|---|---|
| `genlayer_fit` - Meaningful GenLayer usage: the implementation uses GenLayer for a judgment problem that cannot be reduced to deterministic computation | 30 | yes | source file, README |
| `implementation` - Functional implementation: the evidence reasonably demonstrates the claimed implementation exists and performs the described function | 30 | yes | source file, test report, deployment record |
| `documentation` - Documentation quality | 20 | no | README, documentation |
| `deployment` - Evidence of deployment | 20 | no | deployment record |

Pass threshold 60; bands `TIER_A` from 90, `TIER_B` from 75, `TIER_C` from 60.
Required evidence: a README and a source file. Similarity to the starter kit
README blocks the reward. The grant and contribution programs are in
`fixtures/programs.json`.

## Score normalisation

Each criterion earns `2 x weight` for MET, `1 x weight` for PARTIALLY_MET and
nothing otherwise. The score is `earned x 100 // (2 x total weight)`: an
integer from 0 to 100, floored, computed in code. The model is never asked for
a number, and a number in its answer is ignored.

With the hackathon above, both required criteria MET score 60 on their own;
documentation PARTIALLY_MET adds 10; deployment MET adds 20.

## Reward

Only a `PASS` earns: the first band whose `min_score` the score reaches, or
for a grant the milestone's tranche. The reward is reserved from the pool when
the application is filed (the highest band, or the milestone's tranche), so
concurrent passes never over-commit the pool, and paid - never more than was
reserved - when the application is finalized.

## Statuses and reason codes, in precedence order

Code-decided reasons first; the panel is not asked.

| Reason code | Status | Critical | Bond |
|---|---|---|---|
| `PRIMARY_UNAVAILABLE` - the primary item could not be fetched | SOURCE_UNAVAILABLE | no | returned |
| `PRIMARY_CHANGED` - the primary item's bytes no longer match | SOURCE_UNAVAILABLE | no | returned |
| `PRIMARY_UNREADABLE` - too large, not UTF-8, or empty | INSUFFICIENT_EVIDENCE | no | returned |
| `MANIPULATION` - an applicant item addresses the evaluator | FAIL | yes | forfeited |
| `HIDDEN_TEXT` - an applicant item hides or reorders characters | INSUFFICIENT_EVIDENCE | no | returned |
| `DUPLICATE_EVIDENCE` - an applicant item is a program reference, or another applicant filed it to the program first | FAIL | yes | forfeited |
| `APPLICANT_MARK_MISSING` - the primary does not carry the applicant's address | INSUFFICIENT_EVIDENCE | no | returned |
| `REQUIRED_EVIDENCE_UNAVAILABLE` - no item of a required category could be read | SOURCE_UNAVAILABLE | no | returned |

Then the panel's findings, derived by code:

| Reason code | Status | Critical | Bond |
|---|---|---|---|
| `MODEL_OUTPUT_INVALID` - the model's answer was not a usable object | INCONCLUSIVE | no | returned |
| `CLAIM_CONTRADICTED` - the evidence shows an applicant claim is false | FAIL | yes | returned |
| `INELIGIBLE_APPLICANT` - the evidence shows the eligibility policy is not met | INELIGIBLE | no | returned |
| `ELIGIBILITY_UNVERIFIABLE` | INSUFFICIENT_EVIDENCE | no | returned |
| `OFF_TOPIC` - the work is about something else | FAIL | no | returned |
| `RELEVANCE_UNVERIFIABLE` | INSUFFICIENT_EVIDENCE | no | returned |
| `SIMILAR_TO_SOURCE` - repeats a reference (where similarity blocks) | FAIL | no | returned |
| `ORIGINALITY_INCONCLUSIVE` (where similarity blocks) | INCONCLUSIVE | no | returned |
| `REQUIRED_CRITERION_CONFLICTING` | CONFLICTING_EVIDENCE | no | returned |
| `REQUIRED_CRITERION_INSUFFICIENT` | INSUFFICIENT_EVIDENCE | no | returned |
| `REQUIRED_CRITERION_NOT_MET` - NOT_MET or only PARTIALLY_MET | FAIL | no | returned |
| `BELOW_THRESHOLD` | FAIL | no | returned |
| `MEETS_POLICY` | PASS | no | returned |

`reason_codes` in a record lists the reason, plus `SIMILAR_TO_SOURCE` when a
program records similarity without blocking and the panel found it.

## Evidence sufficiency and reachability

| `evidence_sufficiency` | when |
|---|---|
| UNAVAILABLE | status SOURCE_UNAVAILABLE |
| INSUFFICIENT | status INSUFFICIENT_EVIDENCE |
| CONFLICTING | status CONFLICTING_EVIDENCE |
| SUFFICIENT | otherwise |

`source_reachability` is VERIFIED when every item was examined, PARTIAL when
some were not, UNAVAILABLE when the primary was not. Irrelevant evidence is
neither insufficient nor unavailable: a readable item about something else is
`OFF_TOPIC` for the application, or leaves a criterion EVIDENCE_INSUFFICIENT.

## Originality policy

`SIMILAR` is shown from both sides as a run of at least 12 consecutive words.
`SIMILAR_BLOCKS_REWARD` fails the application (`SIMILAR_TO_SOURCE`, bond
returned) and an undecided originality is `INCONCLUSIVE`;
`SIMILAR_RECORDED_ONLY` records the band and lets the criteria decide. Without
references the subject is not asked and the band is `NOT_ASSESSED`. Similarity
is never an accusation of misconduct: only manipulation and duplicate evidence
forfeit a bond.

## Appeal rules

- One appeal per application, by the applicant, while the application is
  EVALUATED and the window is open.
- A reason (up to 600 characters) and up to two new items of allowed
  categories that repeat no committed url or digest.
- The same constitution and policy version; the round reads the appealed
  record's evidence plus exactly the named items.
- The original record is immutable; the appeal record says what it appealed,
  what it read, and whether the original deficiency was resolved.
- An appeal cannot run while evidence the first round read is unreadable.

## Limitations of AI evaluation

A panel of models can misread a subtle technical claim, and honest validators
can disagree about borderline criteria - a disagreement that stores nothing
rather than a wrong answer. Criteria phrased as facts the evidence states or
does not state evaluate far more reliably than criteria asking for taste. The
contract applies the program's policy; it does not decide what the policy
should be.
