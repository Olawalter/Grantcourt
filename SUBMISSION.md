# Submission - GrantCourt

**Evidence-based decisions for hackathons and builder grants.**

A standalone GenLayer Intelligent Contract that applies a program's published,
bounded evaluation constitution to the evidence a builder submits, through a
consensus-backed adjudication, and produces a decision receipt that hackathon
payouts, milestone releases and contribution rewards can consume. Validators
agree on what the evidence shows; code decides what it earns.

**Repository** - https://github.com/Olawalter/Grantcourt

**StudioNet address** - `0x89310fcbA7155d99826934E4e75c273F8f11D709`

**Explorer** - https://explorer-studio.genlayer.com/address/0x89310fcbA7155d99826934E4e75c273F8f11D709

**Deployment transaction** - `0x8741cd475b0d4832c16ce1643e20558f9bbd9dbdc0d8d46969cc135a837d2e23`, FINALIZED, leader execution SUCCESS, votes AGREE x5

**Signer** - `0x85a6304356e9d4970e2F8C4Fd44AeFaA3B8682C1`

**Deployed source** - `contracts/grantcourt.py` at commit `527c0eb`, sha256 `38e42cc1b39f0c809cf3b50de9bd5623889956b30acf4ff8130d520fb54a27e9`, https://github.com/Olawalter/Grantcourt/blob/527c0ebfda9bc7313d0e48544955d550c9baacda/contracts/grantcourt.py - byte-identical on chain (`gen_getContractCode`)

## Why GenLayer is required

Whether a builder is eligible under a written policy, whether a repository
uses GenLayer for a real judgment problem, whether a milestone report is backed
by its deployment record, whether a tutorial is technically correct, and whether
a claim is contradicted by the builder's own evidence are judgments, not facts
a deterministic contract can compute. A single operator's model would make that
operator the authority over who is paid. GrantCourt makes the reading a
consensus of validators who each fetch and verify the hash-bound bytes
themselves, and pays on the agreed result.

## What the contract does

- Programs: an immutable, hashed constitution - eligibility policy, weighted
  criteria with the evidence categories that can pass each, reward bands or
  milestone tranches, originality policy, references, dates, bond, policy
  version - and a GEN pool. Hackathon, builder-grant milestone and
  contribution programs share one trust model.
- Applications commit to the constitution's hash, up to five claims and up to
  six hash-bound evidence items; the reward is reserved at filing.
- Code decides unreadable or changed evidence, text addressed to the
  evaluator, hidden characters, evidence another applicant filed first or that
  is a program reference, a missing applicant mark and unreadable required
  evidence. The panel judges eligibility, relevance, each criterion (met,
  partly, not met, insufficient, conflicting), each claim (supported,
  unsupported, contradicted) and similarity to a named reference; every
  favourable finding quotes the builder's own evidence. Code derives the
  status, score, band or tranche, reward and bond.
- One appeal per application, reading exactly the prior evidence plus the
  named items; the original record is kept.
- A compact receipt (`get_latest_receipt`) with `criterion_result_hash`;
  permissionless finalization and stall exit; pull-payment withdrawal.

## Test and validation results

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

## Live evidence

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

Before the deployment of record, two diagnostic passes on disposable deployments
(`docs/CONSENSUS.md`) changed the panel's reading of exclusion-only eligibility
policies and of conflicting evidence, and a fresh-reader audit found five
defects, all fixed and pinned by tests: evidence now belongs to the first
applicant to file it rather than the first to pass (a copier could otherwise
take an honest applicant's bond), an appeal cannot add evidence from the same
applicant's other filing (one work paid twice), criterion ids cannot shadow the
built-in subjects, a marker phrase that caught "give this project a star" was
narrowed, and a grant must allow a filing per milestone.

## Known limitations

Consensus assumes an honest validator majority, and models can misread a
subtle technical claim. A hash proves bytes did not change since commitment,
not who wrote them or when. Evidence is text up to 12,000 bytes per item;
images and video enter only as transcripts. Eligibility is judged from what the
evidence says. Similarity covers exact byte reuse and repetition of named
references, not the web. Evidence belongs to the first applicant to file it:
a copier who files public evidence before its author is stopped only by the
applicant mark on the primary item. Everything committed is public on chain.
Unaudited; StudioNet is a test network.

## Reviewer fast path

```bash
python -m pytest tests/direct -q
```

```bash
python scripts/deploy_studionet.py --verify
```

Then read `docs/EVALUATION_POLICY.md` (how evidence becomes a decision),
`docs/CONSENSUS.md` (what validators compare, and what the live diagnostic
passes changed) and `docs/SECURITY.md`. The contract is one file,
`contracts/grantcourt.py`.

## Portal description

GrantCourt turns hackathon and builder-grant judging into a GenLayer Intelligent Contract. A program publishes an evaluation constitution - eligibility, weighted criteria with the evidence each needs, reward bands or milestone tranches, originality policy - that no one can change later. Builders file claims and hash-bound evidence committed to that exact policy. Code catches what code can: changed or unreadable evidence, text aimed at the evaluator, hidden characters, reused evidence, missing applicant marks. Validators judge the rest - eligibility, relevance, each criterion including insufficient or conflicting evidence, and whether each claim is supported or contradicted - quoting the builder's own evidence. Code derives the score and payout, one appeal follows, and a compact receipt feeds payout, milestone and reward contracts. Live on StudioNet: 20 of 24 outcomes held, milestones released in order, every payout matched the wallets.
