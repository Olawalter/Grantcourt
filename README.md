<p align="center"><img src="docs/assets/grantcourt-mark.svg" width="140" alt="GrantCourt"/></p>

# GrantCourt - Evidence-Based Decisions for Hackathons and Builder Grants

**A standalone GenLayer Intelligent Contract that applies a published, bounded evaluation policy to the evidence a builder submits, through a consensus-backed adjudication, and produces a decision receipt that hackathon payouts, milestone releases and contribution rewards can consume.**

A program owner fixes an evaluation constitution - who is eligible, the criteria with their weights and the evidence each one needs, the reward bands or milestone tranches, the originality policy, the deadlines, the policy version - and funds a GEN pool. A builder files an application that commits to that constitution's hash: a project description, up to five claims, and up to six evidence items, each bound to the sha256 of its exact bytes. One consensus round has every validator fetch and verify those bytes, check in code what code can check, and answer only what it cannot: is the builder eligible under the written policy, is the work about what the program asks, does the evidence meet each criterion - or is it insufficient, or does it conflict - is each claim supported, unsupported or contradicted, and does it repeat a source the program named. Every finding in the builder's favour quotes the builder's own evidence. Code then derives the status, the score, the band or tranche, and the reward.

No model output ever reaches a status, a score, a band or an amount.

DEPLOYMENT_PENDING

## At a glance

| Question | Answer |
|---|---|
| What is GrantCourt | A reusable contract primitive: an immutable program constitution, hash-bound applications, one consensus evaluation each, one bounded appeal, a compact decision receipt, and a reward ledger. No frontend, backend, database or operator. |
| Who calls it | Hackathon organisers, grant programmes and ecosystem DAOs that create programs; builders who apply; and any contract or indexer that pays on a final receipt (`is_rewardable`, `get_latest_receipt`). |
| What it decides | Eligibility under the program's written policy; relevance to the brief or the milestone; for each criterion MET, PARTIALLY_MET, NOT_MET, EVIDENCE_INSUFFICIENT or EVIDENCE_CONFLICTING; for each claim SUPPORTED, UNSUPPORTED or CONTRADICTED; and similarity to a source the program named. |
| Why GenLayer must decide it | Whether a repository uses GenLayer for a real judgment problem, whether a milestone report is backed by its deployment record, whether a tutorial is technically correct, whether a claim is contradicted by the builder's own test report - none of these is a fact a deterministic contract can compute, and a single operator's model is an authority builders cannot check and a second program cannot reuse. |
| What evidence it uses | The builder's items and the program's reference sources, each committed as url + sha256; every byte is verified before anything reads it. |
| How consensus works | `gl.vm.run_nondet_unsafe` once per evaluation. Each validator reproduces the round from its own fetches and its own model call, gates the leader's payload against its own bytes, and agrees only if what was read matches and its own findings lead to the same status, reason, band, reward, sufficiency, reachability, originality band, critical failure, bond, required-criterion states and contradicted claims. |
| How money moves | Two payable entries (`fund_program`, `submit`), the reward reserved at filing, payment only at `finalize_submission`, one exit (`withdraw`). A refused deposit is returned as a credit, never lost. |
| What tests prove it | VERIFIED_PENDING |

## Deterministic and intelligent responsibilities

| Code decides | Consensus decides |
|---|---|
| identity (every recorded account is the signer), program ownership, the grantee of a grant | eligibility under the written policy |
| the constitution, its hash and the policy version an application commits to | relevance to the brief or the milestone |
| deadlines, the appeal window, the stall window, per-applicant limits, milestone order | each criterion: met, partly met, not met, insufficient, conflicting |
| field limits, accepted submission types and evidence categories, required evidence present | each claim: supported, unsupported, contradicted |
| URL admission, hash verification, unreadable or changed evidence | similarity to a reference source (shown from both sides) |
| text addressed to the evaluator, hidden characters, the applicant mark | |
| evidence another applicant filed first in the program, or that is a program reference | |
| the score, the band or tranche, the status, the bond, the reservation, the ledger | |

The model is never asked for a number. A criterion's score is its weight times 2 for MET, 1 for PARTIALLY_MET, 0 otherwise, normalised to 0-100 in integer arithmetic.

## How it works

### For a program owner

1. `create_program(constitution_json)` - fixed from this moment; its hash is the policy every application commits to.
2. `fund_program(program_id)` with GEN, then `activate_program(program_id)`.
3. `request_evaluation(submission_id)` may be called by the owner or the applicant.
4. `cancel_program` closes intake and honours what was filed; `reclaim_unreserved` returns what no application reserved once intake has closed.

A changed policy is a new program with a higher `evaluation_policy_version` that names the one it `supersedes`. Nothing rewrites a constitution.

### For a builder

1. Publish each evidence item at a stable https URL; put your wallet address in the primary item if the program requires the applicant mark.
2. `submit(program_id, definition_hash, submission_type, milestone_id, project_name, project_description, claims_json, evidence_json)` with exactly the program's bond. The `definition_hash` must be the program's: an application cannot be judged under a policy it did not see.
3. `request_evaluation(submission_id)`.
4. Optionally `appeal(submission_id, reason, items_json)` once inside the window, with up to two new items.
5. `withdraw()` the reward and the returned bond after finalization.

### For anyone

`finalize_submission` and `close_stalled_submission` are permissionless. A builder whose program owner went quiet is never stuck.

## Statuses

| Status | When | Reward | Bond |
|---|---|---|---|
| `PASS` | eligible, relevant, not blocked by similarity, every required criterion MET, score at or above the threshold | the band's reward, or the milestone's tranche | returned |
| `FAIL` | text addressed to the evaluator; evidence another applicant filed first or that is a program reference; a contradicted claim; off-topic; similar to a reference where that blocks; a required criterion not met; below the threshold | none | forfeited for manipulation and duplicate evidence, otherwise returned |
| `INELIGIBLE` | the builder's own evidence shows the eligibility policy is not met | none | returned |
| `INSUFFICIENT_EVIDENCE` | unreadable primary, hidden characters, missing applicant mark, unverifiable eligibility or relevance, a required criterion the evidence does not establish | none | returned |
| `CONFLICTING_EVIDENCE` | two of the builder's items materially contradict each other on a required criterion | none | returned |
| `SOURCE_UNAVAILABLE` | the primary could not be fetched or its bytes changed; no item of a required category could be read | none | returned |
| `INCONCLUSIVE` | the model's answer was unusable, or similarity could not be decided where it blocks | none | returned |

A critical failure - manipulation, duplicate evidence, a contradicted claim - blocks any reward. The full precedence and all 21 reason codes: [`docs/EVALUATION_POLICY.md`](docs/EVALUATION_POLICY.md).

## Three consumers, one trust model

| Program type | Pays | The receipt tells a consumer |
|---|---|---|
| `HACKATHON` | the reward band the score reaches | `reward_band`, `final` |
| `GRANT_MILESTONE` | the milestone's tranche; milestones in order, only by the named grantee | `score_band` is the milestone id on a pass |
| `CONTRIBUTION` | the band for tutorials, articles, translations, integrations | the same fields |

The fixtures define one program of each type. [`docs/INTEGRATION.md`](docs/INTEGRATION.md) shows how a payout contract, a milestone release and a contribution reward each read one receipt.

## Lifecycle

```text
 program    create_program --> DRAFT --fund_program, activate_program--> OPEN
                                 |                                         |
                                 +-------------- cancel_program -----------+--> CANCELLED
                                                                           |
                                                            deadline passes --> CLOSED

 application submit (bond; policy hash checked; evidence locked; reward reserved)
              |
              v
          SUBMITTED --request_evaluation (consensus round)--> EVALUATED
              |                                                  |   appeal window open
              | stall window passes                              |
              v                                                  +--appeal (consensus round)--> APPEAL_EVALUATED
      close_stalled_submission                                   |                                  |
              |                                                  | window closes                    |
              v                                                  v                                  v
      CLOSED_UNRESOLVED                              finalize_submission                  finalize_submission
      (bond returned,                                  |                                   |
       reservation released)                           +--> REWARDED  (reward credited)    +--> REWARDED
                                                       +--> FINALIZED (no reward)          +--> APPEAL_FINALIZED

 anyone     withdraw() pays the caller's claimable credit
```

`EVIDENCE_LOCKED` and `EVALUATING` from the brief's recommended machine are not stored states here: evidence is locked in the same transaction that files it, and an evaluation is one transaction - a round that does not reach consensus stores nothing. Protocol-level disagreement (a round that never reaches a majority) is not the contract's `INCONCLUSIVE`, which is a stored outcome the validators agreed on.

## Appeals

One appeal per application, by the applicant, inside the window. It is a fresh round under the same constitution, reading exactly the appealed round's evidence plus the up to two new items the appeal names - nothing else the applicant committed since. The original record is kept unchanged; the new record carries `appeal_of`, an `evidence_scope` listing both parts, and a `deficiency` block derived in code: the original status and reason, and whether the appeal resolved it. An applicant cannot take down evidence the first round read and appeal for a round that sees less.

## Contract

`contracts/grantcourt.py` - one file, 31 public methods (11 write, 20 view).

| Write | Who | Payable | Notes |
|---|---|---|---|
| `create_program(constitution_json)` | anyone (becomes owner) | no | constitution fixed and hashed |
| `fund_program(program_id)` | owner | yes | a stranger's deposit is returned |
| `activate_program(program_id)` | owner | no | the pool must cover one filing |
| `cancel_program(program_id)` | owner | no | closes intake, honours filed applications |
| `reclaim_unreserved(program_id)` | owner | no | after cancellation or the deadline |
| `submit(...)` | builder | yes, the exact bond | a refused filing's bond is returned |
| `request_evaluation(submission_id)` | applicant or owner | no | one consensus round |
| `appeal(submission_id, reason, items_json)` | applicant | no | once, in the window; one consensus round |
| `finalize_submission(submission_id)` | anyone | no | after the window, or after the appeal |
| `close_stalled_submission(submission_id)` | anyone | no | after the stall window, if never evaluated |
| `withdraw()` | anyone | no | pull payment |

| View | Returns |
|---|---|
| `get_program(program_id)` | constitution, status, pool, reserved, unreserved, paid |
| `get_program_status(program_id, as_of)` | the derived status (CLOSED after the deadline) and whether it accepts filings |
| `get_program_definition_hash(program_id)` | stored and recomputed hash, policy version, supersedes |
| `get_submission(submission_id)` | the application, its locked evidence and digests, policy hash and version, standing result |
| `get_submission_status(submission_id)` | lifecycle status, evaluate-by and appeal deadline |
| `get_actions(submission_id, as_of)` | which action is open at a given time |
| `get_evaluation(submission_id)` | the standing evaluation record |
| `get_evaluation_record(evaluation_id)` | any record, including an appealed one |
| `get_criterion_result(submission_id, criterion_id)` | one criterion's state, basis and weight |
| `get_reward_entitlement(submission_id)` | entitled and pending atto, final |
| `is_rewardable(submission_id)` | rewardable, final, band |
| `get_appeal_state(submission_id)` | the appeal, its window, appeals remaining |
| `get_latest_receipt(submission_id)` | the compact decision receipt |
| `get_milestone_progress(program_id, wallet)` | milestones passed, the next one, an open filing |
| `list_programs`, `list_program_submissions` | pages of ids |
| `get_claimable`, `get_returned_deposits`, `get_stats`, `get_config` | ledger, refused deposits, totals, enums and limits |

## Decision receipt

```text
receipt_version, program_id, submission_id, applicant, evaluation_id,
policy_version, definition_hash, evidence_digests, evidence_commitment,
criterion_result_hash, final_status, reason_codes, score, score_band,
reward_band, reward_atto, critical_failure, originality_band,
evidence_sufficiency, source_reachability, appeal_count,
submission_status, final, finalized_at, record_digest
```

`criterion_result_hash` is the sha256 of every subject's id and state in order; `record_digest` is the sha256 of the full stored record. A consumer can check both against `get_evaluation_record`.

## Originality: what it can and cannot tell

- Evidence whose exact bytes are a reference the program fixed, or were first filed to the program by another applicant: decided by code, a critical failure. Ownership goes to the first to file, never the first to be evaluated, so a copier cannot take evidence by asking for its evaluation first.
- Word-for-word repetition of a reference source: judged by the panel, and SIMILAR must quote a run of at least 12 consecutive words shared by the builder's item and the reference. Shared subject matter and terms are not similarity; paraphrase is not detected.
- The program chooses the consequence: `SIMILAR_BLOCKS_REWARD` or `SIMILAR_RECORDED_ONLY`. Similarity is never an accusation of misconduct; only manipulation and duplicate evidence forfeit a bond.
- Copies of anything else on the web: not seen.

## Verified

LIVE_RUN_PENDING

## Repository

```text
contracts/grantcourt.py                 the contract
tests/direct/                           Direct Mode suite (happy paths, hardening, adversarial)
tests/integration/                      checks against the StudioNet deployment
fixtures/                               program constitutions, evidence texts, four case catalogues
scripts/generate_fixtures.py            writes fixtures/ (--check in CI)
scripts/make_wallets.py                 demo wallets: keys in .data/ (gitignored)
scripts/deploy_studionet.py             deploy, record, verify byte parity
scripts/live_run.py                     the diagnostic pass and the live run
scripts/mutation_check.py               mutation kill check over the contract's guards
scripts/preflight.py                    release gate: documents say only what is true
scripts/fetch_genvm_bundle.py           seeds the GenVM runner cache for the toolchain
deploy/                                 deployment record, live transcript, diagnostics
docs/                                   consensus, evaluation policy, security, adversarial testing, integration, deployment
```

## Getting started

```bash
pip install -r requirements-test.txt
```

```bash
python scripts/fetch_genvm_bundle.py
```

```bash
python scripts/generate_fixtures.py --check
```

```bash
python -m pytest tests/direct -q
```

```bash
genvm-lint check contracts/grantcourt.py --json
```

```bash
python scripts/preflight.py
```

If other GenVM bundles are cached on the machine, pin the linter and the test runner to this one with `GENVM_VERSION=v0.3.0-rc7`. The sample program, application, evaluation, receipt and appeal are exercised end to end by `tests/direct/test_grantcourt.py`; deploying and running them on StudioNet: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Security

Prompt injection, hostile evidence, URL admission and its limits, forged leaders, replay, duplicate evidence, policy versioning, bounded state and failure semantics: [`docs/SECURITY.md`](docs/SECURITY.md) and [`docs/ADVERSARIAL_TESTING.md`](docs/ADVERSARIAL_TESTING.md).

## Limitations

- Consensus assumes an honest validator majority, and models can miss a subtle inaccuracy; criteria work best phrased as facts evidence states or does not.
- A hash proves the bytes did not change since commitment, not who wrote them or when. A URL proves nothing about immutability; the hash does the work.
- Evidence is text: an item over 12,000 bytes is not read, and images and video are admitted only as transcripts.
- Eligibility is judged from what the builder's evidence says; the contract does not verify identity beyond the signing wallet and the applicant mark.
- Similarity covers exact byte reuse and repetition of named references, not the web.
- Everything committed is public on chain.

## Non-goals

GrantCourt does not decide what a program values, which evidence is acceptable, what rewards exist or what follows from each outcome - the program owner writes those into the constitution. It does not claim that AI can objectively decide which builders deserve funding; it applies a published, bounded policy to submitted evidence and records the decision.

## Not production-ready

This is a StudioNet deployment of an unaudited contract. A reward it pays is only as good as the constitution the owner wrote.

## Licence

MIT - see [`LICENSE`](LICENSE).
