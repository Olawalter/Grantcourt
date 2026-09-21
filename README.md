<p align="center"><img src="docs/assets/grantcourt-mark.svg" width="140" alt="GrantCourt"/></p>

# GrantCourt - Evidence-Based Decisions for Hackathons and Builder Grants

**A standalone GenLayer Intelligent Contract that applies a published, bounded evaluation policy to the evidence a builder submits, through a consensus-backed adjudication, and produces a decision receipt that hackathon payouts, milestone releases and contribution rewards can consume.**

A program owner fixes an evaluation constitution - who is eligible, the criteria with their weights and the evidence each one needs, the reward bands or milestone tranches, the originality policy, the deadlines, the policy version - and funds a GEN pool. A builder files an application that commits to that constitution's hash: a project description, up to five claims, and up to six evidence items, each bound to the sha256 of its exact bytes. One consensus round has every validator fetch and verify those bytes, check in code what code can check, and answer only what it cannot: is the builder eligible under the written policy, is the work about what the program asks, does the evidence meet each criterion - or is it insufficient, or does it conflict - is each claim supported, unsupported or contradicted, and does it repeat a source the program named. Every finding in the builder's favour quotes the builder's own evidence. Code then derives the status, the score, the band or tranche, and the reward.

No model output ever reaches a status, a score, a band or an amount.

Deployment of record: [`0x89310fcbA7155d99826934E4e75c273F8f11D709`](https://explorer-studio.genlayer.com/address/0x89310fcbA7155d99826934E4e75c273F8f11D709) on GenLayer StudioNet (chain 61999), from commit `527c0eb`, byte-identical to `contracts/grantcourt.py`.

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
| What tests prove it | 255 Direct Mode tests across every status and reason code, band boundaries, hostile evidence, forged leader payloads through the captured validator, appeals and money conservation; a 74-of-74 mutation sweep; GenVM lint; two live diagnostic passes and a 115-transaction live run on StudioNet. See "Verified". |

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

| Check | Result |
|---|---|
| `python -m pytest tests/direct -q` | 255 passed |
| `genvm-lint check contracts/grantcourt.py --json` | lint ok, validation ok, 31 methods (20 view, 11 write); one I200 notice that a newer runner exists |
| `ruff check .` | clean |
| `python scripts/generate_fixtures.py --check` | fixtures match (53 files) |
| `python scripts/mutation_check.py --jobs 3` | on the deployed contract: 74 of 74 mutations killed (`deploy/mutation_sweep_final.txt`); the earlier sweep's three survivors and the guards added since are recorded in `deploy/mutation_sweep.txt` and `deploy/mutation_recheck.txt` |
| `python scripts/deploy_studionet.py --verify` | byte-identical, 31 schema methods |
| `python -m pytest tests/integration -q` | 7 passed, 1 skipped (the opt-in live write) |
| CI (`.github/workflows/ci.yml`) | green on every pushed commit |
| Clean clone | install, ruff, fixture check, 255 Direct Mode tests and the GenVM lint pass on a fresh clone; no `.data/` is committed |
| `python scripts/preflight.py` | every check passes |

The live run of record on `0x89310fcbA7155d99826934E4e75c273F8f11D709`: 115 transactions from 2026-09-21T19:48:19Z to 2026-09-21T21:46:27Z, none of them a rejected round (`deploy/live_run_transcript.json`, `deploy/live_run.log`). Fixtures were served from `https://raw.githubusercontent.com/Olawalter/Grantcourt/2b9f427/fixtures/`. Amounts are the catalogue's divided by 10 (`LIVE_SCALE`); every rule, band and threshold is the catalogue's. Seven program instances - one hackathon, three for the adversarial cases, two builder grants and one contribution program - plus one for the stall exit.

| Case | Expected | Observed | Decided by | Held |
|---|---|---|---|---|
| [HK01](https://explorer-studio.genlayer.com/tx/0x8270a360f7a25c14f85810650068e5087fa61e1110030d94004a261775ddcffd) | PASS / MEETS_POLICY / TIER_A | PASS / MEETS_POLICY / TIER_A | PANEL | yes |
| [HK02](https://explorer-studio.genlayer.com/tx/0xca1c9dd74ef63b222de633f25aebd5ecf179d72b96048c236f27b97823feeae3) | FAIL / REQUIRED_CRITERION_NOT_MET / NONE | FAIL / REQUIRED_CRITERION_NOT_MET / NONE | PANEL | yes |
| [HK03](https://explorer-studio.genlayer.com/tx/0x36cd2f51712d9fe016dbe11ada546fc2cd5ba66a8a2b4b0b61154e0ddea5b7e1) | PASS / MEETS_POLICY / TIER_C | FAIL / REQUIRED_CRITERION_NOT_MET / NONE | PANEL | **no** |
| [HK04](https://explorer-studio.genlayer.com/tx/0x09f514aa276ec4da8a9b86b9b5a82f6535e326735437b5fd91b64293f8ff5aa2) | FAIL / CLAIM_CONTRADICTED / NONE | FAIL / CLAIM_CONTRADICTED / NONE | PANEL | yes |
| [HK05](https://explorer-studio.genlayer.com/tx/0x9330e96fd5ba73db51579b6dbd05dbfc91d30e71a691c8033ac679cc8b720390) | CONFLICTING_EVIDENCE / REQUIRED_CRITERION_CONFLICTING / NONE | CONFLICTING_EVIDENCE / REQUIRED_CRITERION_CONFLICTING / NONE | PANEL | yes |
| [HK06](https://explorer-studio.genlayer.com/tx/0xd281b0e613981b5a25ad1099d9b5a0893a326aa7f9861750528b32cdcce87cb7) | INSUFFICIENT_EVIDENCE / REQUIRED_CRITERION_INSUFFICIENT / NONE | FAIL / REQUIRED_CRITERION_NOT_MET / NONE | PANEL | **no** |
| [HK06:appeal](https://explorer-studio.genlayer.com/tx/0x8a3ae9fa8d66d8d04afb7c7fbfa1de9a67962066e6a54bdc6e55b18c48f3e330) | PASS / MEETS_POLICY / TIER_C | FAIL / REQUIRED_CRITERION_NOT_MET / NONE | PANEL | **no** |
| [GM01](https://explorer-studio.genlayer.com/tx/0xc158ec86af21bc9429e76414cfc14e29863eb1500a8e744aa6862c286e0f794e) | PASS / MEETS_POLICY / M1 | PASS / MEETS_POLICY / M1 | PANEL | yes |
| [GM02](https://explorer-studio.genlayer.com/tx/0xe911cddae1625b75c23ecd874ee6d2fa0000b79fc494d071d62c6f3bbbfaa65c) | PASS / MEETS_POLICY / M2 | PASS / MEETS_POLICY / M2 | PANEL | yes |
| [GM03](https://explorer-studio.genlayer.com/tx/0x91647022154f10039e7b4409d380552ca57da4eff26d4b4f3861a94fbd2d9856) | FAIL / CLAIM_CONTRADICTED / NONE | FAIL / CLAIM_CONTRADICTED / NONE | PANEL | yes |
| [CT01](https://explorer-studio.genlayer.com/tx/0x2e86b62aaed6134c1deecf936ab30699e715ee06f1294f6909a848fbeb88daf6) | PASS / MEETS_POLICY / FULL | PASS / MEETS_POLICY / FULL | PANEL | yes |
| [CT02](https://explorer-studio.genlayer.com/tx/0x67222f7bd97aba9bad9bfc4d8a4ae05cfc4ca295186d2e6a7cd6472d5c72e28b) | FAIL / SIMILAR_TO_SOURCE / NONE | FAIL / SIMILAR_TO_SOURCE / NONE | PANEL | yes |
| [CT03](https://explorer-studio.genlayer.com/tx/0x3a55b8219e1abdf324b41ab50514b7ad469575d5f21ab6fed5d9f447ba5f4b62) | FAIL / OFF_TOPIC / NONE | FAIL / OFF_TOPIC / NONE | PANEL | yes |
| [CT04](https://explorer-studio.genlayer.com/tx/0x93e48f4ad8c41dbfae7e34d853d134a9b85f43c2071b56d0e7e5ec40b020867e) | INELIGIBLE / INELIGIBLE_APPLICANT / NONE | INELIGIBLE / INELIGIBLE_APPLICANT / NONE | PANEL | yes |
| [AD01](https://explorer-studio.genlayer.com/tx/0x72ba3c213154601ac45cb5ab0f904dafc2451bea3c5cae04007faa4701d0e6b1) | FAIL / MANIPULATION / NONE | FAIL / MANIPULATION / NONE | CODE | yes |
| [AD02](https://explorer-studio.genlayer.com/tx/0x8e6ef501a2c4e539427657d3ff4635036ab4c6aa0224e7ec7019d508c460d4b4) | FAIL / MANIPULATION / NONE | FAIL / MANIPULATION / NONE | CODE | yes |
| [AD03](https://explorer-studio.genlayer.com/tx/0xb9d54c726edcb65ef9790b6b72e7c4fb24a63299f3c5368aaaac5e0f27f1e7bf) | FAIL / MANIPULATION / NONE | FAIL / MANIPULATION / NONE | CODE | yes |
| [AD04](https://explorer-studio.genlayer.com/tx/0xa85dc356af15c5af0915d54b133023873ae2fd1dc3dbfe91ebf088af661c5219) | FAIL / MANIPULATION / NONE | FAIL / MANIPULATION / NONE | CODE | yes |
| [AD05](https://explorer-studio.genlayer.com/tx/0x385f92aa18625a6f62457799196a63f56964a82caa9ab26835f748f3959b571b) | INSUFFICIENT_EVIDENCE / HIDDEN_TEXT / NONE | INSUFFICIENT_EVIDENCE / HIDDEN_TEXT / NONE | CODE | yes |
| [AD06](https://explorer-studio.genlayer.com/tx/0x5596c4ffa29d70dd239766d5a869a271eb960f7dd92fb78a8c914633210f0b70) | INSUFFICIENT_EVIDENCE / APPLICANT_MARK_MISSING / NONE | INSUFFICIENT_EVIDENCE / APPLICANT_MARK_MISSING / NONE | CODE | yes |
| [AD07](https://explorer-studio.genlayer.com/tx/0xf03545da2122cb4c23f7020a53cb62467cf90c1c4b71720d19956e5ea458adf0) | FAIL / DUPLICATE_EVIDENCE / NONE | FAIL / DUPLICATE_EVIDENCE / NONE | CODE | yes |
| [AD08](https://explorer-studio.genlayer.com/tx/0xd4e52b160c1d2e884dee99dbcd2b313484d6d8bb01be01f591951cc6e5a81513) | FAIL / CLAIM_CONTRADICTED / NONE | FAIL / CLAIM_CONTRADICTED / NONE | PANEL | yes |
| [AD09](https://explorer-studio.genlayer.com/tx/0xae64bdd7a94a1f22a0547d3a9cd76a9c70200703f20b0858900619bb5ca694a0) | FAIL / REQUIRED_CRITERION_NOT_MET / NONE | FAIL / OFF_TOPIC / NONE | PANEL | **no** |
| [DUP](https://explorer-studio.genlayer.com/tx/0xc1cd8bb4d1d139a269d6c594e46fac67205661840224bef453fe130da2bce109) | FAIL / DUPLICATE_EVIDENCE / NONE | FAIL / DUPLICATE_EVIDENCE / NONE | CODE | yes |

20 of 24 outcomes held; every code-decided outcome held.

Four outcomes did not hold, and the contract did what the program's rules say in each:

- **HK03, HK06 and HK06's appeal** - the panel read the required criterion `implementation` ("the evidence reasonably demonstrates that the claimed implementation exists and performs the described function") as PARTIALLY_MET, for evidence that is a contract excerpt plus a test report (HK03, and HK06's appeal once the complete source was added) or a source file that only points elsewhere (HK06's first round). The fixtures expected MET for HK03 and the appeal, and EVIDENCE_INSUFFICIENT for HK06's first round. The example constitution requires a required criterion to be fully MET, so each failed with `REQUIRED_CRITERION_NOT_MET`. The panels split along model lines: in HK03 and the HK06 appeal a lone GPT validator read it MET and was outvoted; in the first diagnostic pass the same HK03 evidence read MET. This is panel variance on a borderline criterion under a strict rule, reported as observed; the appeal still read exactly the prior evidence plus the two named items (`evidence_scope` E1-E3 + E4, E5) and recorded the unresolved deficiency.
- **AD09** - the rubric-redefinition attempt failed as intended, with nothing paid, but as `OFF_TOPIC` (relevance read IRRELEVANT) rather than the expected `REQUIRED_CRITERION_NOT_MET`; the first diagnostic pass showed the same split.

| What | Result |
|---|---|
| Evidence filed again by another applicant | [bob filed alice's HK01 evidence](https://explorer-studio.genlayer.com/tx/0xc1cd8bb4d1d139a269d6c594e46fac67205661840224bef453fe130da2bce109): `DUPLICATE_EVIDENCE`, bond forfeited - the first filer owns its evidence |
| Builder grant, milestones in order | M1 passed and settled, releasing its tranche; only then was M2 [filed and evaluated](https://explorer-studio.genlayer.com/tx/0xe911cddae1625b75c23ecd874ee6d2fa0000b79fc494d071d62c6f3bbbfaa65c): PASS, M2 tranche released; `get_milestone_progress` read 1 then 2 of 2 passed; an M2 filed before M1 passed was [refused](https://explorer-studio.genlayer.com/tx/0xba1fcaf5d5b7d38e9718c3ce5b3bc8d68468262ba0afddc697392fa7a6fd93b7) |
| Appeal | [HK06's appeal](https://explorer-studio.genlayer.com/tx/0x8a3ae9fa8d66d8d04afb7c7fbfa1de9a67962066e6a54bdc6e55b18c48f3e330) read the prior evidence plus exactly the two named items; it did not resolve the deficiency (see above) |
| Finalization | 23 applications settled; rewarded: CT01, GM01, GM02, HK01; bonds forfeited for AD01, AD02, AD03, AD04, AD07, DUP |
| Stall exit | an unevaluated application was [closed](https://explorer-studio.genlayer.com/tx/0xb6350004ae019c67453daebda98fbde914081c056650a4b7918149d717cd9d4e) `CLOSED_UNRESOLVED` after its window, the early close and a stranger's evaluation request refused; the program was [cancelled](https://explorer-studio.genlayer.com/tx/0xd90f14426d91af4de3669e2ba11c81d736a8f7533c90317f0ad66d305df73aa3) and its pool [reclaimed](https://explorer-studio.genlayer.com/tx/0x8c62b48a1681c4fa36446f5be77ef38f7c28a318464abb28c8872bc03b101237) |
| Refusals | 11 sent as real transactions, every one refused with its sentence: a stranger's appeal, a second appeal, a second evaluation, a stranger activating a program, reclaiming an open pool, finalizing inside an open appeal window, a milestone out of order, a stranger requesting an evaluation, closing before the stall window; and two payable refusals that returned the bond as a credit - the owner applying to its own program, and a policy version mismatch |
| Withdrawals | alice 0.0096 GEN, bob 0.0017 GEN, carol 0.0012 GEN, dave 0.0012 GEN, erin 0.0090 GEN, owner 0.0027 GEN; each wallet rose by exactly its amount |
| Ledger | the contract's chain balance, 107500000000000000 atto, equals the pools, bonds and credits it accounts for (107500000000000000 in unspent program pools, no bonds, no credits) |

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
