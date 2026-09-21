# Decision record

Why this contract, why this shape, and why GenLayer.

## The problem

Hackathons and builder-grant programmes receive more applications than people
can read consistently. The questions that decide payment are not arithmetic:
does the project use GenLayer for a real judgment problem, does the milestone
report match the deployment record, is the tutorial technically correct, does
the README's claim survive the builder's own test report. A smart contract can
enforce deadlines, hashes, permissions and amounts; it cannot read a
repository against an evaluation brief written in English.

## Candidates considered

| # | Candidate | Verdict | Reason |
|---|---|---|---|
| 1 | GrantCourt: an immutable evaluation constitution, hash-bound applications with explicit claims, one consensus evaluation, a bounded appeal, a compact receipt, funded rewards and milestone tranches | chosen | the judgment is semantic, the evidence is public and checkable, and a reward or tranche moves on the result |
| 2 | A committee-voting module with an AI summary for each reviewer | rejected | reviewers stay the bottleneck and the authority; the model has no consequence |
| 3 | An AI scoring oracle that returns a number per application | rejected | a model's number deciding payment is exactly what the brief rules out; nothing binds it to published criteria |
| 4 | A GitHub-activity heuristic (commits, stars, CI badges) | rejected | deterministic and gameable; fails the delete-GenLayer test by construction |
| 5 | A full grant-management platform with a frontend | rejected | out of scope by the brief; the primitive is the contract |

## Portfolio collision analysis

This portfolio already holds a close neighbour, **ContributionCourt**
(community-content campaigns). The user chose to differentiate rather than
merge or skip. What is shared is deliberate reuse of engineering proven on
StudioNet: hash-bound fetching, the URL admission rules, quote grounding by
contiguous word runs, the structural gate, voting on leader errors by prefix,
consensus on consequence, and the pull-payment ledger with returned deposits.
What differs is the trust question and the evidence model:

| | ContributionCourt | GrantCourt |
|---|---|---|
| The question | is this piece of community content on task, substantive and original | does this builder's evidence satisfy a program's published criteria, and are the builder's own claims true |
| Evidence | one work plus cited sources | up to six typed items (README, source file, deployment record, test report, milestone report, transcript, article...) with categories the program allows and requires |
| What a criterion can say | satisfied, partly, not, unverifiable | met, partly met, not met, **evidence insufficient**, **evidence conflicting** - the brief's distinction between insufficient, unavailable, conflicting and irrelevant evidence |
| Claims | none | up to five explicit applicant claims, each judged supported, unsupported or **contradicted**; a contradiction is a critical failure |
| Eligibility | none | a written eligibility policy judged by the panel; a named grantee enforced by code |
| Evidence per criterion | none | each criterion names the evidence categories that can pass it; a finding quoting any other item does not stand |
| Payout shapes | reward bands | reward bands, or **milestone tranches released in order** |
| Policy binding | spec hash stored | the application commits to the constitution's hash and is refused on a mismatch; the receipt names the policy version |
| Appeal | contributor or owner; adds sources | applicant only; reads exactly the prior evidence plus the named items, and records whether the original deficiency was resolved |
| Receipt | the evaluation record | a compact receipt with `criterion_result_hash` for downstream contracts |

Against other builds in this portfolio: agent-work escrows judge one
deliverable against one buyer's order; milestone escrows release one payee's
funds on one definition with no published multi-criterion rubric; prize-pool
courts rank entries against each other, while GrantCourt judges each
application alone against a fixed constitution and pays per band or tranche.

## Ecosystem collision analysis

Hackathon platforms (Devpost-style judging), grant platforms (Gitcoin-style
rounds, milestone-based grant programmes) and on-chain bounty boards keep the
judgment with human reviewers or with voting; payouts follow a decision made
off chain. Grant-scoring tools that use models return a score from one
operator's model. GrantCourt is none of these: it is the adjudication step as
a contract - a published constitution, validator consensus on what the
evidence shows, deterministic arithmetic, and a receipt any payout system can
read - with no platform, dashboard or voting around it.

## Why GenLayer is necessary

The decisive questions - is the builder eligible under the written policy, is
the work relevant, is each criterion met by the evidence, is each claim
supported or contradicted - have no deterministic answer. A single operator
could run a model, but then the operator is the authority: builders cannot
check it, a second programme cannot reuse it, and the operator decides who is
paid. GenLayer makes the reading a consensus of independent validators, each
fetching and verifying the bytes itself, and lets the contract hold and pay the
reward on the agreed result.

## The delete-GenLayer test

> Can a conventional deterministic smart contract safely decide whether a
> hackathon submission or builder-grant milestone satisfies a natural-language
> evaluation policy using heterogeneous public evidence?

Remove the consensus round and what remains: deadlines, bonds, reservations,
policy hashes, milestone order, the grantee check, hash verification, duplicate
and reference evidence, applicant marks and injection markers still work.
Nothing can say whether the builder is eligible, whether the work is relevant,
whether a criterion is met, or whether a claim is true. Every application would
either be paid on filing or sent to a committee - the original problem. The
contract without GenLayer is a bond escrow with a milestone counter.

## The three-consumer proof

One contract, one trust model, three programme shapes, all in the fixtures:

1. **Hackathon payouts** - `HACKATHON`: four weighted criteria, three reward
   tiers; a payout contract pays `reward_band` on a final receipt.
2. **Builder grant milestones** - `GRANT_MILESTONE`: a named grantee, two
   milestones in order, a tranche per milestone; a milestone contract releases
   the next tranche when the receipt for `M1` is final and passed.
3. **Ecosystem contribution rewards** - `CONTRIBUTION`: tutorials and
   articles judged for accuracy, usefulness and completeness, similarity to a
   named reference blocking the reward.

[`docs/INTEGRATION.md`](docs/INTEGRATION.md) shows each consumer's read.

## Hardest technical risk

Consensus on subjective findings. Honest models disagree about whether a
README "partly" or "fully" meets a documentation criterion, and about which
sentence to quote. The design keeps what validators compare to what changes a
consequence: the status and reason, the band and reward, sufficiency,
reachability, the originality band, a critical failure, the bond, the state of
each required criterion and the list of contradicted claims. Optional criteria
moving inside one band, notes and quote choice are recorded and never compared.
A finding that would help or harm the builder must quote the evidence it rests
on, re-grounded by every validator in its own verified bytes, so a model
cannot invent support. The live diagnostic pass on a disposable deployment is
where this risk is measured; its findings are recorded in
[`docs/CONSENSUS.md`](docs/CONSENSUS.md).

## Why a standalone Intelligent Contract

The constitution, the evidence commitments, the evaluation, the appeal, the
receipt and the money must live in one place that no party controls. Split
across a backend and a token contract, the backend becomes the judge. As one
contract, the whole decision - rules, evidence, reading and payment - is
inspectable and reusable by any programme that writes a constitution.
