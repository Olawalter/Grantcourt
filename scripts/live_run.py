#!/usr/bin/env python3
"""Run GrantCourt on GenLayer StudioNet with real transactions.

    python scripts/live_run.py <address> --raw-base <url> --phase cases
    python scripts/live_run.py <address> --raw-base <url> --phase full

--raw-base is a commit-pinned https://raw.githubusercontent.com/.../fixtures/
URL, so every validator fetches exactly the committed bytes.

cases: the diagnostic pass. The programs are created and funded, every
       catalogue case is filed and evaluated once, and each evaluation's
       per-node stdout ([DISAGREE], [MINE], [DOWNGRADE]) is recorded, so a
       split names its cause. Written to deploy/diagnostics/.
full:  the live run of record. The same cases, plus the applicant's appeal
       with new evidence, evidence that passed for one applicant filed by
       another, refusals sent as real transactions, finalization of every
       evaluated submission after its window, the builder grant's second
       milestone filed only after the first settled, a stall exit, every
       withdrawal checked against the wallet's balance, and the contract's
       balance checked against what it says it holds.
       Written to deploy/live_run_transcript.json.

Amounts are the catalogue's divided by LIVE_SCALE, so the run moves little
GEN; every band, threshold and rule is the catalogue's own.

Code-decided outcomes are asserted: the run stops if one differs. Panel-
decided outcomes are recorded with held=true/false and never stop the run.
Every transaction hash is saved before its receipt is awaited, so an
interrupted run resumes without resending anything. Keys come from
.data/demo_wallets.json (gitignored) and are never printed.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import studionet_transport  # noqa: E402,F401 - retries RPC transport failures
from genlayer_py import create_account, create_client  # noqa: E402
from genlayer_py.chains import studionet  # noqa: E402
from genlayer_py.types import TransactionStatus  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
KEYS = ROOT / ".data" / "demo_wallets.json"
RPC = "https://studio.genlayer.com/api"
WAIT = dict(interval=5000, retries=360)
GEN = 10 ** 18
LIVE_SCALE = 10
APPEAL_WINDOW = 900
LONG_STALL = 4 * 3600
SHORT_STALL = 120
T: dict = {}
OUT = ROOT / "deploy" / "live_run_transcript.json"

PROGRAMS_FILE = json.loads((FIXTURES / "programs.json").read_text(encoding="utf-8"))
PROGRAMS = PROGRAMS_FILE["programs"]
HASHES = PROGRAMS_FILE["hashes"]
CASES = {}
for _name in ("hackathon_submissions.json", "builder_grant_milestones.json",
              "contribution_submissions.json", "adversarial_submissions.json"):
    for _case in json.loads((FIXTURES / _name).read_text(encoding="utf-8"))["cases"]:
        CASES[_case["case_id"]] = _case
CODE_REASONS = ("PRIMARY_UNAVAILABLE", "PRIMARY_CHANGED", "PRIMARY_UNREADABLE", "MANIPULATION",
                "HIDDEN_TEXT", "DUPLICATE_EVIDENCE", "APPLICANT_MARK_MISSING",
                "REQUIRED_EVIDENCE_UNAVAILABLE")
# live program instance -> (catalogue program, cases filed to it). Cases sharing an
# evidence file with the same applicant go to different instances: one applicant
# cannot commit the same bytes twice to one program.
INSTANCES = {
    "hackathon": ("hackathon", ["HK01", "HK02", "HK03", "HK04", "HK05", "HK06"]),
    "adv-1": ("hackathon", ["AD01", "AD02", "AD05", "AD06"]),
    "adv-2": ("hackathon", ["AD03", "AD07", "AD08", "AD09"]),
    "adv-3": ("hackathon", ["AD04"]),
    "grant": ("grant", ["GM01"]),
    "grant-b": ("grant", ["GM03"]),
    "contribution": ("contribution", ["CT01", "CT02", "CT03", "CT04"]),
}


def log(*parts):
    print(*parts, flush=True)


def save():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(T, indent=2, sort_keys=True, default=str) + "\n",
                   encoding="utf-8", newline="\n")


def die(message: str):
    log("FATAL:", message)
    T["fatal"] = message
    save()
    raise SystemExit(1)


def check(condition, message: str):
    if not condition:
        die(message)


def retry(action, attempts=8, pause=20):
    last = None
    for attempt in range(attempts):
        try:
            return action()
        except Exception as err:          # noqa: BLE001 - transport errors vary
            last = err
            log(f"    transient ({attempt + 1}/{attempts}): {str(err)[:120]}")
            time.sleep(pause)
    raise last


def now_iso(offset: int = 0) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def epoch(iso: str) -> int:
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def wait_until(iso: str, why: str, margin: int = 30):
    remaining = epoch(iso) + margin - int(time.time())
    if remaining > 0:
        log(f"  waiting {remaining}s {why}")
        time.sleep(remaining)


def rpc(method: str, params: list):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(RPC, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "grantcourt-live-run"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def node_lines(tx: str) -> list:
    """Each node's model, vote and stdout tail for one transaction."""
    try:
        result = retry(lambda: rpc("eth_getTransactionByHash", [tx]))["result"]
    except Exception:                     # noqa: BLE001
        return []
    cd = result.get("consensus_data") or {}
    out = []
    for n in (cd.get("leader_receipt") or [])[:1] + (cd.get("validators") or []):
        nc = n.get("node_config") or {}
        out.append({"mode": n.get("mode"), "model": (nc.get("primary_model") or {}).get("model"),
                    "vote": (cd.get("votes") or {}).get(nc.get("address")),
                    "stdout": ((n.get("genvm_result") or {}).get("stdout") or "")[-900:]})
    return out


def leader_result(receipt) -> str:
    leader = receipt["consensus_data"]["leader_receipt"]
    entry = leader[0] if isinstance(leader, list) else leader
    return str(entry["execution_result"])


def votes(receipt) -> list:
    last_round = receipt.get("last_round") or {}
    named = last_round.get("validator_votes_name")
    if named:
        return [str(v) for v in named]
    mapping = (receipt.get("consensus_data") or {}).get("votes") or {}
    return [str(v).upper() for v in mapping.values()]


def accepted(receipt) -> bool:
    cast = [v.upper() for v in votes(receipt)]
    return sum(v.startswith("AGREE") for v in cast) > sum(v.startswith("DISAGREE") for v in cast)


def verify_fixtures(raw: str):
    """Every location a live round reads must serve exactly the local bytes."""
    for rel, digest in sorted(HASHES.items()):
        try:
            with urllib.request.urlopen(raw + rel, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as err:
            die(f"{raw + rel} is not reachable: {err}")
        check(hashlib.sha256(body).hexdigest() == digest,
              f"{raw + rel} does not serve the committed bytes")
    log(f"  verified {len(HASHES)} source locations against local bytes")


class Actor:
    def __init__(self, address: str, name: str, key: str):
        self.name = name
        self.address = address
        self.account = create_account(key)
        self.client = create_client(chain=studionet, account=self.account)
        self.wallet = self.account.address.lower()

    def read(self, fn: str, args: list):
        return retry(lambda: self.client.read_contract(address=self.address, function_name=fn,
                                                       args=args))

    def balance(self) -> int:
        return int(retry(lambda: self.client.get_balance(self.account.address)))

    def funded(self, at_least: int):
        balance = self.balance()
        if balance >= at_least:
            return
        log(f"  funding {self.name} from the faucet (balance {balance})")
        retry(lambda: self.client.fund_account(self.account.address, GEN))
        for _ in range(40):
            if self.balance() > balance:
                return
            time.sleep(5)
        die("the faucet did not fund " + self.name)

    def write(self, step: str, fn: str, args: list, expect: str = "SUCCESS", value: int = 0,
              attempts: int = 3) -> dict:
        """One transaction, recorded under a step name and never resent. A
        round the panel could not agree on is asked again: nothing it did
        applied, and the next round draws a different panel."""
        done = T.setdefault("steps", {})
        if step in done:
            return done[step]
        pending = T.setdefault("pending", {})
        record = {}
        for attempt in range(attempts):
            if step in pending:
                tx = pending[step]
                log(f"  {self.name}.{fn} resuming {tx}")
            else:
                if value:
                    self.funded(value * 2)
                tx = retry(lambda: self.client.write_contract(
                    address=self.address, function_name=fn, args=args, value=value,
                    consensus_max_rotations=3))
                tx = tx if isinstance(tx, str) else tx.hex()
                pending[step] = tx
                save()
                log(f"  {self.name}.{fn} tx {tx}")
            receipt = retry(lambda: self.client.wait_for_transaction_receipt(
                transaction_hash=tx, status=TransactionStatus.FINALIZED, **WAIT))
            result = leader_result(receipt)
            record = {"step": step, "actor": self.name, "method": fn, "tx": tx,
                      "status": str(receipt.get("status_name") or receipt.get("status")),
                      "leader_execution": result, "votes": votes(receipt),
                      "accepted": accepted(receipt)}
            leader = receipt["consensus_data"]["leader_receipt"]
            payload = (leader[0].get("result") or {}).get("payload") \
                if isinstance(leader, list) else None
            if payload is not None:
                record["returned"] = str(payload)[:300]
            if value:
                record["value_atto"] = str(value)
            log(f"    {record['status']} leader {result} votes {record['votes']}")
            del pending[step]
            save()
            if expect != "SUCCESS" or result != "SUCCESS" or record["accepted"]:
                break
            T.setdefault("rejected_rounds", []).append(dict(record, nodes=node_lines(tx)))
            log(f"    the panel did not agree ({attempt + 1}/{attempts}); asking again")
            save()
        done[step] = record
        save()
        check(record["leader_execution"] == expect,
              f"{step}: leader execution {record['leader_execution']}, expected {expect}")
        check(expect != "SUCCESS" or record["accepted"],
              f"{step}: the panel did not agree after {attempts} rounds")
        return record


def actors(address: str) -> dict:
    keys = json.loads(KEYS.read_text(encoding="utf-8"))
    return {name: Actor(address, name, key) for name, key in keys.items()}


def scaled(atto: str) -> str:
    return str(int(atto) // LIVE_SCALE)


def live_spec(name: str, raw: str, **overrides) -> dict:
    data = json.loads(json.dumps(PROGRAMS[name]))
    for ref in data["reference_sources"]:
        ref["url"] = ref["url"].replace("{BASE}", raw)
    for band in data["reward_bands"]:
        band["reward_atto"] = scaled(band["reward_atto"])
    for milestone in data["milestones"]:
        milestone["tranche_atto"] = scaled(milestone["tranche_atto"])
    # the catalogue's dates stand; only the windows shrink to what a live run can wait out
    data.update({"appeal_window_seconds": APPEAL_WINDOW, "stall_window_seconds": LONG_STALL,
                 "submission_bond_atto": scaled(data["submission_bond_atto"])})
    data.update(overrides)
    return data


def filing_reserve(data: dict, milestone_id: str = "") -> int:
    if data["program_type"] == "GRANT_MILESTONE":
        return int([m for m in data["milestones"] if m["milestone_id"] == milestone_id][0]
                   ["tranche_atto"])
    return int(data["reward_bands"][0]["reward_atto"])


def program(ac: dict, key: str, name: str, raw: str, filings: int, **overrides) -> str:
    ids = T.setdefault("programs", {})
    owner = ac["owner"]
    data = live_spec(name, raw, **overrides)
    if key not in ids:
        before = owner.read("list_programs", [0, 50])["total"]
        owner.write("create:" + key, "create_program", [json.dumps(data)])
        page = owner.read("list_programs", [0, 50])
        check(page["total"] == before + 1, "create_program did not add a program")
        ids[key] = page["items"][-1]
        T.setdefault("constitutions", {})[key] = data
        save()
    pid = ids[key]
    reserve = max(filing_reserve(data, m["milestone_id"]) for m in data["milestones"]) \
        if data["milestones"] else filing_reserve(data)
    pool = reserve * filings
    held = int(owner.read("get_program", [pid])["pool_atto"])
    if held < pool:
        owner.write("fund:" + key + ":" + str(pool), "fund_program", [pid], value=pool - held)
    if owner.read("get_program", [pid])["status"] == "DRAFT":
        owner.write("activate:" + key, "activate_program", [pid])
    return pid


def evidence(triples, raw: str) -> str:
    return json.dumps([{"category": cat, "url": raw + "sources/" + rel,
                        "sha256": HASHES["sources/" + rel], "label": label}
                       for rel, cat, label in triples])


def submit(ac: dict, step: str, pid: str, case_id: str, raw: str, applicant: str = None,
           definition_hash: str = None, expect: str = "SUCCESS") -> str:
    case = CASES[case_id]
    who = ac[applicant or case["applicant"]]
    view = ac["stranger"].read("get_program", [pid])
    bond = int(view["constitution"]["submission_bond_atto"])
    args = [pid, definition_hash or view["definition_hash"], case["submission_type"],
            case["milestone_id"], case["project_name"], case["project_description"],
            json.dumps(case["claims"]), evidence(case["evidence"], raw)]
    record = who.write(step, "submit", args, value=bond, expect=expect)
    returned = record.get("returned", "")
    if not step.startswith("refuse:"):
        check("RETURNED" not in returned, f"{step}: the filing was refused: {returned}")
    return returned


def submission_of(ac: dict, pid: str, case_id: str, applicant: str = None) -> str:
    wallet = ac[applicant or CASES[case_id]["applicant"]].wallet
    primary = HASHES["sources/" + CASES[case_id]["evidence"][0][0]]
    page = ac["stranger"].read("list_program_submissions", [pid, 0, 50])
    for sid in reversed(page["items"]):
        sub = ac["stranger"].read("get_submission", [sid])
        if sub["applicant"] == wallet and sub["items"][0]["sha256"] == primary:
            return sid
    die(f"no submission found for {case_id}")


def outcome(ac: dict, key: str, sid: str, expected: list, tx: str) -> dict:
    if key in T.get("outcomes", {}):
        # resuming: a recorded outcome stands; the standing record may be a later round's
        return T["outcomes"][key]
    record = ac["stranger"].read("get_evaluation", [sid])
    got = [record["status"], record["reason_code"], record["score_band"]]
    code = expected[1] in CODE_REASONS
    held = got == expected
    row = {"submission_id": sid, "evaluation_id": record["evaluation_id"], "tx": tx,
           "expected": expected, "observed": got, "decided_by": "CODE" if code else "PANEL",
           "held": held, "overall_score": record["overall_score"],
           "reward_atto": record["reward_atto"], "critical_failure": record["critical_failure"],
           "originality_band": record["originality_band"],
           "evidence_sufficiency": record["evidence_sufficiency"],
           "source_reachability": record["source_reachability"],
           "criterion_results": [[f["id"], f["state"], f["by"]]
                                 for f in record["criterion_results"]],
           "rows": [[r["evidence_id"], r["status"]] for r in record["rows"]],
           "markers": record["markers"], "hidden": record["hidden"],
           "applicant_mark": record["applicant_mark"],
           "duplicate_items": record["duplicate_items"],
           "evidence_scope": record["evidence_scope"],
           "criterion_result_hash": record["criterion_result_hash"],
           "record_digest": record["record_digest"]}
    if not held:
        row["nodes"] = node_lines(tx)
    T.setdefault("outcomes", {})[key] = row
    save()
    log(f"  {key}: {' / '.join(got)} ({row['decided_by']}) held={held}")
    if code and not held:
        die(f"{key}: code-decided outcome {got}, expected {expected}")
    return record


def file_and_evaluate(ac: dict, pid: str, case_id: str, raw: str, key: str = None,
                      applicant: str = None, expected: list = None) -> str:
    key = key or case_id
    submit(ac, "submit:" + key, pid, case_id, raw, applicant=applicant)
    sid = submission_of(ac, pid, case_id, applicant)
    T.setdefault("submissions", {})[key] = sid
    step = ac["owner"].write("evaluate:" + key, "request_evaluation", [sid])
    outcome(ac, key, sid, expected or CASES[case_id]["expected"], step["tx"])
    return sid


def run_cases(ac: dict, raw: str, full: bool, only: list = None) -> dict:
    pids = {}
    instances = {k: (n, [c for c in cs if not only or c in only])
                 for k, (n, cs) in INSTANCES.items()}
    instances = {k: v for k, v in instances.items() if v[1]}
    for key, (name, cases) in instances.items():
        # full: the reused-evidence filing, and the grant's second milestone
        extra = 1 if key in ("hackathon", "grant") and full else 0
        pids[key] = program(ac, key, name, raw, len(cases) + extra,
                            title=PROGRAMS[name]["title"] + " (" + key + ")",
                            per_applicant_limit=10)
    for key, (_name, cases) in instances.items():
        for case_id in cases:
            sid = file_and_evaluate(ac, pids[key], case_id, raw)
            case = CASES[case_id]
            if full and case.get("appeal_items"):
                who = ac[case["applicant"]]
                step = who.write("appeal:" + case_id, "appeal",
                                 [sid, case["appeal_reason"],
                                  evidence(case["appeal_items"], raw)])
                outcome(ac, case_id + ":appeal", sid, case["appeal_expected"], step["tx"])
    if full:
        if T["outcomes"]["HK01"]["held"]:
            # the evidence that passed for alice, filed by bob
            file_and_evaluate(ac, pids["hackathon"], "HK01", raw, key="DUP", applicant="bob",
                              expected=["FAIL", "DUPLICATE_EVIDENCE", "NONE"])
        else:
            T.setdefault("notes", []).append("HK01 did not pass live, so the reused-evidence "
                                             "case had no passed evidence to reuse; it is "
                                             "covered by the Direct Mode suite only")
    return pids


def refusals(ac: dict, pids: dict, raw: str):
    """Real transactions the contract must refuse, each with its sentence."""
    subs = T["submissions"]
    stranger = ac["stranger"]
    tries = [
        ("refuse:stranger_appeals", stranger, "appeal", [subs["HK01"], "I disagree.", "[]"],
         "only the applicant can appeal"),
        ("refuse:second_appeal", ac["carol"], "appeal", [subs["HK06"], "Again.", "[]"],
         "only an EVALUATED submission can be appealed, once"),
        ("refuse:evaluate_twice", ac["owner"], "request_evaluation", [subs["HK01"]],
         "only a SUBMITTED application awaits its evaluation"),
        ("refuse:stranger_activates", stranger, "activate_program", [pids["grant"]],
         "only the program owner activates it"),
        ("refuse:reclaim_open_pool", ac["owner"], "reclaim_unreserved", [pids["hackathon"]],
         "an OPEN program's pool is reclaimed after its deadline"),
    ]
    open_now = [sid for sid in subs.values()
                if stranger.read("get_submission", [sid])["status"] == "EVALUATED"
                and epoch(stranger.read("get_submission", [sid])["appeal_deadline"])
                > time.time() + 300]
    if open_now:
        tries.append(("refuse:early_finalize_open_window", stranger, "finalize_submission",
                      [open_now[-1]], "the appeal window is open until"))
    else:
        T.setdefault("notes", []).append("no submission had an open appeal window when the "
                                         "refusals ran; the early-finalize refusal is covered "
                                         "by the Direct Mode suite only")
    held = []
    for step, who, fn, args, sentence in tries:
        record = who.write(step, fn, args, expect="ERROR")
        check(sentence in record.get("returned", ""), f"{step}: refusal said {record}")
        held.append(step)
    # an out-of-order milestone: the grant pays no bond, so the refusal raises
    record = ac["erin"].write("refuse:milestone_out_of_order", "submit", [
        pids["grant-b"], stranger.read("get_program", [pids["grant-b"]])["definition_hash"],
        "MILESTONE_DELIVERABLE", "M2", "Settlement adapter", "M2 filed early.", "[]",
        evidence(CASES["GM02"]["evidence"], raw)], expect="ERROR")
    check("milestones are evaluated in order" in record.get("returned", ""),
          f"out-of-order milestone: {record}")
    held.append("refuse:milestone_out_of_order")
    # payable refusals return the deposit instead of raising
    bond = int(stranger.read("get_program", [pids["contribution"]])["constitution"]
               ["submission_bond_atto"])
    for step, applicant, digest, sentence in (
            ("refuse:owner_applies", "owner", None, "a program owner cannot apply"),
            ("refuse:policy_mismatch", "alice", "0" * 64, "policy version mismatch")):
        before = int(stranger.read("get_claimable", [ac[applicant].wallet])["claimable_atto"])
        returned = submit(ac, step, pids["contribution"], "CT01", raw, applicant=applicant,
                          definition_hash=digest)
        check("RETURNED" in returned and sentence in returned, f"{step}: {returned}")
        after = int(stranger.read("get_claimable", [ac[applicant].wallet])["claimable_atto"])
        check(after - before == bond, f"{step}: the refused deposit was not credited back")
        held.append(step)
    T["refusals"] = held
    save()
    log(f"  {len(held)} refusals held")


def stall(ac: dict, raw: str) -> str:
    pid = program(ac, "stall", "contribution", raw, 1,
                  title="Ecosystem tutorials (stall demonstration)",
                  stall_window_seconds=SHORT_STALL)
    submit(ac, "submit:stall", pid, "CT01", raw)
    sid = submission_of(ac, pid, "CT01")
    T["stall_submission"] = sid
    ac["stranger"].write("refuse:stranger_evaluates", "request_evaluation", [sid],
                         expect="ERROR")
    ac["stranger"].write("refuse:early_close", "close_stalled_submission", [sid], expect="ERROR")
    sub = ac["stranger"].read("get_submission", [sid])
    wait_until(time.strftime("%Y-%m-%dT%H:%M:%SZ",
                             time.gmtime(epoch(sub["submitted_at"]) + SHORT_STALL)),
               "for the stall window")
    ac["stranger"].write("close_stalled", "close_stalled_submission", [sid])
    check(ac["stranger"].read("get_submission", [sid])["status"] == "CLOSED_UNRESOLVED",
          "the stalled submission did not close")
    ac["owner"].write("cancel:stall", "cancel_program", [pid])
    ac["owner"].write("reclaim:stall", "reclaim_unreserved", [pid])
    view = ac["stranger"].read("get_program", [pid])
    check(view["status"] == "CANCELLED" and view["pool_atto"] == "0",
          f"cancel and reclaim left {view}")
    return pid


def settle(ac: dict, keys=None):
    stranger = ac["stranger"]
    keys = keys or sorted(T["submissions"])
    deadlines = [epoch(stranger.read("get_submission", [T["submissions"][k]])["appeal_deadline"])
                 for k in keys
                 if stranger.read("get_submission", [T["submissions"][k]])["appeal_deadline"]]
    if deadlines:
        wait_until(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(max(deadlines))),
                   "for every appeal window to close")
    for key in keys:
        sid = T["submissions"][key]
        if stranger.read("get_submission", [sid])["status"] in ("EVALUATED", "APPEAL_EVALUATED"):
            stranger.write("finalize:" + key, "finalize_submission", [sid])
        sub = stranger.read("get_submission", [sid])
        receipt = stranger.read("get_latest_receipt", [sid])
        T.setdefault("settled", {})[key] = dict(
            {k: sub[k] for k in ("status", "reward_atto", "bond_outcome", "finalized_at")},
            receipt={k: receipt[k] for k in (
                "final_status", "reason_codes", "score", "reward_band", "reward_atto",
                "criterion_result_hash", "definition_hash", "policy_version", "final")})
        save()


def second_milestone(ac: dict, raw: str, pids: dict):
    """The grant's M2 opens only once M1 passed and settled."""
    progress = ac["stranger"].read("get_milestone_progress", [pids["grant"], ac["erin"].wallet])
    T["milestone_progress_before_m2"] = progress
    if progress["next_milestone"] != "M2":
        T.setdefault("notes", []).append("M1 did not pass live, so M2 was not filed")
        save()
        return
    file_and_evaluate(ac, pids["grant"], "GM02", raw)
    settle(ac, ["GM02"])
    T["milestone_progress_after_m2"] = ac["stranger"].read(
        "get_milestone_progress", [pids["grant"], ac["erin"].wallet])
    save()


def withdrawals(ac: dict):
    for name, actor in ac.items():
        owed = int(actor.read("get_claimable", [actor.wallet])["claimable_atto"])
        if owed <= 0:
            continue
        before = actor.balance()
        actor.write("withdraw:" + name + ":" + str(owed), "withdraw", [])
        after = before
        for _ in range(24):
            after = actor.balance()
            if after - before >= owed:
                break
            time.sleep(5)
        check(after - before == owed,
              f"{name} withdrew {owed} but the wallet moved {after - before}")
        T.setdefault("withdrawn", {})[name] = str(owed)
        save()
        log(f"  {name} withdrew {owed} atto; its wallet rose by exactly that")


def ledger(ac: dict, address: str):
    stats = ac["stranger"].read("get_stats", [])
    balance = int(retry(lambda: ac["stranger"].client.get_balance(address)))
    T["ledger"] = {"stats": stats, "contract_balance_atto": str(balance)}
    save()
    check(int(stats["held_atto"]) == balance,
          f"the contract holds {balance} but accounts for {stats['held_atto']}")
    log(f"  contract balance {balance} atto equals what it accounts for")


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("--raw-base", required=True)
    parser.add_argument("--phase", choices=("cases", "full"), required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--only", default="", help="cases phase: comma-separated case ids")
    args = parser.parse_args()
    raw = args.raw_base if args.raw_base.endswith("/") else args.raw_base + "/"
    if args.out:
        OUT = pathlib.Path(args.out)
    elif args.phase == "cases":
        OUT = ROOT / "deploy" / "diagnostics" / ("cases_" + args.address.lower()[:10] + ".json")
    if OUT.exists():
        T.update(json.loads(OUT.read_text(encoding="utf-8")))
    T.update({"address": args.address, "raw_base": raw, "phase": args.phase,
              "network": "studionet", "live_scale": LIVE_SCALE})
    T.setdefault("started_at", now_iso())
    save()
    ac = actors(args.address)
    log("wallets:", ", ".join(f"{n} {a.wallet}" for n, a in ac.items()))
    verify_fixtures(raw)
    for name in ac:
        ac[name].funded(100 * 10 ** 15 if name != "owner" else 400 * 10 ** 15)
    full = args.phase == "full"
    only = [c for c in args.only.split(",") if c] if not full else None
    pids = run_cases(ac, raw, full, only)
    if full:
        refusals(ac, pids, raw)
        stall(ac, raw)
        settle(ac)
        second_milestone(ac, raw, pids)
        withdrawals(ac)
        ledger(ac, args.address)
    outcomes = T.get("outcomes", {})
    T["summary"] = {"held": sorted(k for k, v in outcomes.items() if v["held"]),
                    "not_held": sorted(k for k, v in outcomes.items() if not v["held"])}
    T["finished_at"] = now_iso()
    save()
    log("DONE", json.dumps(T["summary"]))


if __name__ == "__main__":
    main()
