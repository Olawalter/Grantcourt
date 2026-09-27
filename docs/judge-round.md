# Judge round - 27 September 2026

The judges asked for matching updated source and deployment that correct the
post-appeal evidence commitment:

> After appeal evidence is appended, `get_submission()` currently returns the
> expanded items and digests but retains the pre-appeal `evidence_commitment`.
> Update the stored commitment when the item list changes, or expose clearly
> separated original and current commitments so every returned commitment
> matches the item list it describes.

The finding was accurate, confirmed by reading the code before any change.

## What was wrong

Evidence is hash-bound at filing. An appeal may append at most two new items, and
the appeal round reads the appealed round's items plus those, so a submission's
item list can grow exactly once.

`appeal` did grow it - `sub.items = _canonical(items)` - and did not touch
`sub.evidence_commitment`, which had been computed at filing and was never
recomputed. From then on `get_submission` returned:

- `items`: five entries, the expanded list;
- `evidence_digests`: those five digests;
- `evidence_commitment`: the sha256 over the three entries as filed.

The answer therefore did not check against itself. A reader recomputing the
commitment from the item list beside it would have found a mismatch and had no
way to tell which list the published commitment described.

**What was not wrong, and why nothing was mis-paid.** Consensus compares the
commitment of the round it is judging, not the submission's field: `_ctx` computes
`evidence_commitment` from the items that round reads, every validator compares
it, and the stored evaluation record keeps it. The appeal round's record already
carried the commitment of the expanded list, and the appealed round's record the
commitment of the list as filed. No reward, band or bond outcome depended on the
stale field. What it damaged was verifiability - which is the only reason to
publish a commitment at all.

## What changed

Both halves of the remedy, rather than one:

- the stored commitment now moves with the list it describes. `appeal`
  recomputes `sub.evidence_commitment` from the expanded list in the same place
  it writes the list;
- the list as filed is kept under its own name. `Submission.filed_commitment` is
  written once, at filing, and never rewritten;
- `get_submission` returns both, plus what a reader needs to interpret them:

| Field | Over which list |
|---|---|
| `evidence_commitment` | the `items` and `evidence_digests` in that same answer |
| `filed_evidence_commitment` | the list as filed |
| `evidence_appended_by_appeal` | true exactly when the two differ |
| `item_count` | the length of the current list |

- each evaluation record continues to carry the commitment of the list **its own
  round** read. That was already correct; it is now stated in
  [`INTEGRATION.md`](INTEGRATION.md#which-commitment-describes-which-list) and in
  the README, so all three commitments are documented with the list each is over.

There is now no commitment anywhere in the contract's answers that describes a
list other than the one printed beside it.

## How it is pinned

**Tests** (`tests/direct/test_grantcourt_hardening.py`):

- an appeal that appends evidence: the commitment moves, the filed commitment
  does not, the moved one is the sha256 of the canonical item list the same
  answer returns, `evidence_digests` are that list's digests in order, and
  `evidence_appended_by_appeal` is true;
- an appeal that adds nothing: both commitments stay equal and the list is
  unchanged;
- every stored round checked against its own list, for both rounds of an
  appealed submission.

**Mutations** (`scripts/mutation_check.py`), each killed by the suite:

- "an appeal leaves the submission's commitment describing the list as filed" -
  the regression itself;
- "the filed commitment is overwritten instead of kept" - the other direction,
  where separating the two would be lost.

The sweep was re-run on the corrected contract: **76 of 76 killed, 0 survived**
(`deploy/mutation_sweep_letter.txt`). The Direct Mode suite is 258 tests.

## Matching source and deployment

| Item | Value |
|---|---|
| Contract | `0x768E30F335E6Ff12a5244b9274d56d30F37d0674` |
| Source commit | `adadc47803e6880ff07914c6aa905029131deb23` |
| Source sha256, and the deployed source read back with `gen_getContractCode` | equal - byte-identical |
| Receipt | FINALIZED, leader execution SUCCESS, votes AGREE x5 |

`python scripts/deploy_studionet.py --verify` re-checks that pairing on demand,
and a clean clone of this repository reproduces the same sha256. The deployment
the review read, `0x89310fcbA7155d99826934E4e75c273F8f11D709`, and its live run
are kept under `deploy/superseded/0x89310fcb/`.

## Proved on the deployment, not only in tests

One submission was filed, evaluated and appealed against the corrected
deployment, and a read-only script then checked every commitment against the list
beside it:

```bash
python scripts/letter_proof.py 0x768E30F335E6Ff12a5244b9274d56d30F37d0674 --submission GS-000002
```

Eleven checks, all passed (`deploy/letter_proof_0x768e30f3.json`):

| Check | Observed |
|---|---|
| `get_submission`'s commitment is over the items it returns | equal |
| the digests returned are those items' digests, in order | equal |
| `item_count` is the length of that list | 5 |
| two rounds were judged | EV-000002, EV-000003 |
| the filed commitment is the first round's commitment | equal |
| the appeal appended evidence | 3 items -> 5 |
| `evidence_appended_by_appeal` says so | true |
| the current commitment is the appeal round's commitment | equal |
| the two commitments differ, as the two lists do | differ |
| each round carries the commitment of the list it read | both |

The transactions are recorded in `deploy/letter_run_0x768e30f3.json` (program,
funding, activation, submission, evaluation) and
`deploy/letter_appeal_0x768e30f3.json` (the appeal that appended two hash-bound
items).

**What this proof does not claim.** The evaluation outcome of that submission is a
panel reading, and HK06 is one of the two cases whose reading the judged run
already reported as variable. The proof asserts the commitments and the item
list, nothing about the panel's verdict.

## Why the demo wallets differ from the judged run

The judged run's demo wallet private keys were never in the repository, and the
local copy was lost before this round. Every evidence source carries the
applicant's wallet as its authorship mark, so the corpus was regenerated for
fresh wallets through the repository's own workflow - `scripts/make_wallets.py`,
then `scripts/generate_fixtures.py` - which is byte-for-byte reproducible and
checked in CI (`--check`). The superseded run keeps its own transcript and pinned
commit, so the earlier evidence stays readable at the commit it was served from.
