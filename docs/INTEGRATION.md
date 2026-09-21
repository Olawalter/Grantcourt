# Integration

One receipt, three consumers, one trust model. A downstream system never
re-judges an application: it reads GrantCourt's final receipt and applies its
own rule.

## The rule every consumer applies

Pay or release only when both hold:

```text
receipt = get_latest_receipt(submission_id)
receipt["found"] and receipt["final"] and receipt["final_status"] == "PASS"
```

`final` means the application was finalized: its appeal window closed or its
appeal was heard, and no method can change the record again. A `PASS` that is
not yet final can still be overturned by the applicant's appeal and must not
be paid on. `is_rewardable(submission_id)` returns the same two facts as
`rewardable` and `final`.

A consumer that wants to bind the decision to the policy it trusts also checks
`receipt["definition_hash"]` against the constitution hash it recorded when it
chose to consume that program (`get_program_definition_hash`), and may check
`criterion_result_hash` and `record_digest` against
`get_evaluation_record(receipt["evaluation_id"])`.

## Consumer 1 - hackathon payouts

A hackathon's prize contract pays each tier from its own treasury, using
GrantCourt only as the judge (a program can also fund GrantCourt's own pool and
let `withdraw` pay; the two are alternatives).

```python
@gl.contract_interface
class GrantCourt:
    class View:
        def get_latest_receipt(self, submission_id: str) -> dict: ...

PRIZES = {"TIER_A": 3000, "TIER_B": 1500, "TIER_C": 500}

@gl.public.write
def claim_prize(self, submission_id: str) -> None:
    r = GrantCourt(self.court).view().get_latest_receipt(submission_id)
    if not (r["found"] and r["final"] and r["final_status"] == "PASS"):
        raise gl.vm.UserError("not a final pass")
    if r["program_id"] != self.program_id or r["definition_hash"] != self.policy_hash:
        raise gl.vm.UserError("a different program or policy")
    if submission_id in self.paid:
        raise gl.vm.UserError("already paid")
    self.paid[submission_id] = r["applicant"]
    self.credit(r["applicant"], PRIZES[r["reward_band"]])
```

## Consumer 2 - builder grant milestones

A grant escrow holds the grant and releases the next tranche only on a final,
passed receipt for the next milestone. The milestone id is the receipt's
`score_band` on a pass; `get_milestone_progress(program_id, grantee)` gives the
count GrantCourt itself enforces (milestones are filed in order, only by the
grantee).

```python
@gl.public.write
def release_next(self, submission_id: str) -> None:
    r = GrantCourt(self.court).view().get_latest_receipt(submission_id)
    want = "M" + str(self.released + 1)
    if not (r["found"] and r["final"] and r["final_status"] == "PASS"):
        raise gl.vm.UserError("milestone not finally passed")
    if r["program_id"] != self.program_id or r["score_band"] != want:
        raise gl.vm.UserError("not the next milestone of this grant")
    self.released += 1
    self.credit(self.grantee, self.tranches[want])
```

## Consumer 3 - ecosystem contribution rewards

A DAO paying reputation points or tokens for tutorials, translations and
integrations reads the same receipt. Because `reason_codes` and
`critical_failure` are in the receipt, it can also keep a record of who was
refused for manipulation or duplicate evidence without re-reading anything.

```python
@gl.public.write
def record_contribution(self, submission_id: str) -> None:
    r = GrantCourt(self.court).view().get_latest_receipt(submission_id)
    if not r["final"]:
        raise gl.vm.UserError("wait for the final receipt")
    if r["final_status"] == "PASS":
        self.points[r["applicant"]] = self.points.get(r["applicant"], 0) + 10
    elif r["critical_failure"]:
        self.flags[r["applicant"]] = r["reason_codes"][0]
```

These sketches show the read; each consumer adds its own storage and payment.

## Off-chain consumers

Dashboards and indexers read the same views over JSON-RPC:

```python
client.read_contract(address=COURT, function_name="get_latest_receipt", args=[sid])
client.read_contract(address=COURT, function_name="list_program_submissions",
                     args=[program_id, 0, 50])
client.read_contract(address=COURT, function_name="get_criterion_result",
                     args=[sid, "genlayer_fit"])
```

Views have no clock: time-dependent questions take an `as_of` argument
(`get_program_status`, `get_actions`), and every write checks its own
transaction time.

## Receipt fields

| Field | Meaning |
|---|---|
| `receipt_version` | 1 |
| `program_id`, `submission_id`, `applicant`, `evaluation_id` | what was judged, whose, and which record stands |
| `policy_version`, `definition_hash` | the constitution it was judged under |
| `evidence_digests`, `evidence_commitment` | the sha256 of every item read, in order, and of the item list |
| `criterion_result_hash` | sha256 of every subject's id and state |
| `final_status`, `reason_codes` | the outcome |
| `score`, `score_band`, `reward_band`, `reward_atto` | the arithmetic and what it pays |
| `critical_failure`, `originality_band`, `evidence_sufficiency`, `source_reachability` | the qualifiers |
| `appeal_count`, `submission_status`, `final`, `finalized_at` | where the application is |
| `record_digest` | sha256 of the full stored record |
