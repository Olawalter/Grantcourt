#!/usr/bin/env python3
"""Mutation kill check: prove the Direct Mode suite pins each load-bearing
guard, not merely that the code passes today.

For each mutation the repository is copied to a scratch directory with ONE
guard in the contract mechanically broken, and the whole Direct Mode suite
runs against the copy. A mutation is KILLED when the suite fails and SURVIVED
when it passes (an unpinned guard). The run starts with an accept-control:
the unmodified copy must pass, or every kill would be vacuous.

Anchors are code TEXT, never line numbers. An anchor that is not found
exactly once is reported as ANCHOR MISSING - the guard moved or was deleted,
which is its own finding.

Run:  python scripts/mutation_check.py              (full sweep)
      python scripts/mutation_check.py --anchors    (anchor check only)
      python scripts/mutation_check.py --only gate  (names containing "gate";
                                                     separate several with |)
      python scripts/mutation_check.py --jobs 3     (three scratch copies)
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = "contracts/grantcourt.py"
Q = '"'


def off(condition: str) -> tuple:
    """(anchor, replacement) turning one `if` line into `if False:`."""
    head = condition[:len(condition) - len(condition.lstrip())]
    keyword = condition.lstrip().split(" ", 1)[0]
    return (condition + "\n", head + keyword + " False:\n")


def m(name: str, anchor: str, replacement: str = None) -> tuple:
    if replacement is None:
        anchor, replacement = off(anchor)
    return (name, anchor, replacement)


MUTATIONS = [
    # -- evidence --------------------------------------------------------------------
    m("changed bytes are read as the committed evidence",
      '    if hashlib.sha256(body).hexdigest() != item["sha256"]:'),
    m("an oversized item is read anyway", "    if len(body) > FETCH_BYTES_CAP:"),
    # -- what code decides before any model --------------------------------------------
    m("text addressed to the evaluator is not manipulation",
      "    if any(e in markers for e in own):"),
    m("hidden characters are not caught", "    if any(e in hidden for e in own):"),
    m("duplicate evidence is not decided in code", '    if len(ctx["duplicate_items"]) > 0:'),
    m("the applicant mark is not required",
      '    if ctx["require_applicant_mark"] and not applicant_mark:'),
    m("unreadable required evidence is not caught", "        if len(readable) == 0:"),
    m("a program's reference passed off as work is not a duplicate",
      '            if it["sha256"] in refs or other:\n', "            if other:\n"),
    m("evidence that passed for another applicant is not a duplicate",
      '            if it["sha256"] in refs or other:\n', '            if it["sha256"] in refs:\n'),
    m("an applicant's own passed evidence is its own duplicate",
      ' \\\n                and str(self.submissions.get(str(holder)).applicant) != str(sub.applicant)',
      ""),
    m("the last filer, not the first, owns the evidence",
      "            if self.first_commits.get(first) is None:\n"
      "                self.first_commits[first] = submission_id\n",
      "            self.first_commits[first] = submission_id\n"),
    m("an appeal may add evidence from the applicant's other filing",
      "            if self._committed_elsewhere(str(sub.program_id), str(sub.applicant), e,"),
    m("a failed filing keeps its evidence from the applicant's next filing",
      "        if record[\"status\"] != PASS:\n            self._release_items(sub)\n",
      ""),
    m("a passed filing releases its evidence",
      "        if record[\"status\"] != PASS:\n            self._release_items(sub)\n",
      "        self._release_items(sub)\n"),
    m("a criterion id may shadow a built-in subject",
      "    if text.upper() in BUILT_IN_SUBJECTS or _is_claim_id(text.upper()):"),
    m("a grant may allow fewer filings than milestones",
      '    if spec["per_applicant_limit"] < len(spec["milestones"]):'),
    # -- support rules -----------------------------------------------------------------
    m("two quotes sharing one word are a similarity",
      '        return any(_shared_run(a["text"], b["text"]) >= COPY_RUN_WORDS\n',
      '        return any(_shared_run(a["text"], b["text"]) >= 1\n'),
    m("a similarity needs thirteen shared words", "COPY_RUN_WORDS = 12 ", "COPY_RUN_WORDS = 13 "),
    m("an eligibility finding needs no quote",
      "        return state == UNVERIFIABLE or len(own) > 0\n", "        return True\n"),
    m("a relevance finding needs no quote",
      "        return state not in (RELEVANT, PARTIALLY_RELEVANT) or len(own) > 0\n",
      "        return True\n"),
    m("a claim finding needs no quote",
      "        return state == UNSUPPORTED or len(own) > 0\n", "        return True\n"),
    m("a passing criterion may quote any category",
      '        return any(categories[q["evidence_id"]] in wanted for q in own)\n',
      "        return len(own) > 0\n"),
    m("a criterion naming no categories needs no quote",
      "        if len(wanted) == 0:\n            return len(own) > 0\n",
      "        if len(wanted) == 0:\n            return True\n"),
    m("conflicting evidence may be quoted from one item",
      '        return len(set(q["evidence_id"] for q in own)) >= 2\n',
      '        return len(set(q["evidence_id"] for q in own)) >= 1\n'),
    m("a reference source counts as the applicant's evidence",
      '    own = [q for q in quotes if roles.get(q["evidence_id"]) in APPLICANT_ROLES]\n',
      "    own = quotes\n"),
    # -- the derivation -----------------------------------------------------------------
    m("an unusable model answer is judged anyway",
      '    if payload["panel_state"] != PANEL_ASSESSED:\n        return (INCONCLUSIVE',
      "    if False:\n        return (INCONCLUSIVE"),
    m("a contradicted claim does not fail",
      '    if any(_state_of(payload, k["claim_id"]) == CONTRADICTED for k in ctx["claims"]):'),
    m("an ineligible applicant is judged anyway", "    if eligibility == NOT_ELIGIBLE:"),
    m("unverifiable eligibility is judged anyway", "    if eligibility == UNVERIFIABLE:"),
    m("off-topic work is judged anyway", "    if relevance == IRRELEVANT:"),
    m("unverifiable relevance is judged anyway", "    if relevance == UNVERIFIABLE:"),
    m("similar work is not blocked", "        if originality == SIMILAR:"),
    m("inconclusive originality is not blocked", "        if originality == INCONCLUSIVE:"),
    m("recorded-only similarity blocks the reward",
      '    if ctx["has_references"] and ctx["originality_policy"] == "SIMILAR_BLOCKS_REWARD":\n',
      '    if ctx["has_references"]:\n'),
    m("conflicting required evidence is not conflicting",
      "    if EVIDENCE_CONFLICTING in states:"),
    m("insufficient required evidence is not insufficient",
      "    if EVIDENCE_INSUFFICIENT in states:"),
    m("a required criterion only partly met passes", "    if any(s != MET for s in states):"),
    m("the threshold score itself fails",
      '    if _score(ctx, payload) >= ctx["pass_threshold"]:\n',
      '    if _score(ctx, payload) > ctx["pass_threshold"]:\n'),
    m("partly met earns full points", "CRITERION_POINTS = {MET: 2, PARTIALLY_MET: 1,",
      "CRITERION_POINTS = {MET: 2, PARTIALLY_MET: 2,"),
    m("a band's own min score misses the band", '        if score >= b["min_score"]:\n',
      '        if score > b["min_score"]:\n'),
    m("a manipulation keeps its bond",
      '"bond_outcome": BOND_FORFEIT if reason in FORFEIT_REASONS else BOND_RETURN,',
      '"bond_outcome": BOND_RETURN,'),
    m("no failure is critical", '"critical_failure": reason in CRITICAL_REASONS,',
      '"critical_failure": False,'),
    # -- consensus ----------------------------------------------------------------------
    m("required criteria are compared after an earlier reason decided",
      "        if reason in CRITERIA_DECIDED else {},\n", "        if True else {},\n"),
    m("required criteria are never compared",
      "        if reason in CRITERIA_DECIDED else {},\n", "        if False else {},\n"),
    m("the consequence is not compared",
      '        if mine[key] != theirs[key]:\n            return key + " mine="',
      '        if False:\n            return key + " mine="'),
    m("what each node read is not compared",
      "        difference = _evidence_difference(own, parsed)\n", '        difference = ""\n'),
    m("the gate trusts the leader's code reason", '    if p["panel_reason"] != reason:'),
    m("the gate does not re-ground quotes",
      "        if q in seen or not _quote_grounded(q, eligible, texts):\n",
      "        if q in seen:\n"),
    m("a model failure is ratified",
      "    if leader_text.startswith(ERROR_LLM):\n        return False\n", ""),
    # -- filing ---------------------------------------------------------------------------
    m("a stale policy version is accepted",
      "        if definition_hash != str(program.definition_hash):"),
    m("the owner may apply to its own program", "        if wallet == str(program.owner):"),
    m("anyone may file a grantee's milestones",
      '        if spec["grantee"] != "" and wallet != spec["grantee"]:'),
    m("milestones may be filed out of order", "            if milestone_id != wanted:"),
    m("a milestone may have two open filings",
      '            if slot is not None and str(slot) != "":'),
    m("required evidence may be missing", "    if missing:"),
    m("one item may count twice",
      '        if e["url"] in seen or e["sha256"] in seen:\n            return "evidence must',
      '        if False:\n            return "evidence must'),
    m("the per-applicant limit does not hold",
      '        if count is not None and int(count) >= spec["per_applicant_limit"]:'),
    m("an applicant may file the same evidence twice",
      '            if self._committed_elsewhere(program_id, wallet, e, ""):'),
    m("the pool may be over-reserved",
      "        if int(program.pool_atto) - int(program.reserved_atto) < reserve:"),
    m("filings are taken before the program opens",
      '        if at < _iso_epoch(spec["opens_at"]):'),
    m("a refused deposit is kept by raising",
      '            if value > 0:\n                return self._return_deposit("submit", err)\n',
      '            if False:\n                return self._return_deposit("submit", err)\n'),
    m("applicant text may address the evaluator",
      "    if _evaluator_hits(value) or _hidden_hits(value):"),
    m("an IP literal is a host", "    if all_numeric or labels[-1].isdigit():"),
    m("the lowest band need not start at the threshold",
      '    if bands[len(bands) - 1]["min_score"] != threshold:'),
    m("a superseding program may keep the old version",
      '            if spec["evaluation_policy_version"] <= '
      'self._spec(prior)["evaluation_policy_version"]:'),
    m("the owner may be its own grantee", '        if spec["grantee"] == owner:'),
    # -- rounds, appeals, settlement ------------------------------------------------------
    m("anyone may request an evaluation",
      "        if wallet != str(sub.applicant) and wallet != str(program.owner):"),
    m("an evaluation may run after the stall window",
      '        if _iso_epoch(now) > _iso_epoch(str(sub.submitted_at)) + '
      'spec["stall_window_seconds"]:'),
    m("anyone may appeal", "        if self._sender_hex() != str(sub.applicant):"),
    m("an appeal may be filed after its window",
      "        if _iso_epoch(now) > _iso_epoch(str(sub.appeal_deadline)):\n"
      '            self._fail("the appeal window closed',
      '        if False:\n            self._fail("the appeal window closed'),
    m("an appellant may take down its own evidence", "        if lost:"),
    m("a submission may be finalized inside its appeal window",
      "            if _iso_epoch(now) <= _iso_epoch(str(sub.appeal_deadline)):"),
    m("a passed milestone never advances the grant", "        if passed:"),
    m("a withdrawal does not clear the ledger",
      "        self.credits[wallet] = u256(0)\n        self.credits_total_atto",
      "        self.credits_total_atto"),
]


def run_suite(workdir: pathlib.Path) -> bool:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/direct", "-q", "-x", "-p", "no:cacheprovider",
         "--no-header"], cwd=workdir, capture_output=True, text=True)
    return completed.returncode == 0


def check_anchors(source: str) -> int:
    missing = 0
    for name, old, _new in MUTATIONS:
        hits = source.count(old)
        if hits != 1:
            print(f"ANCHOR MISSING ({hits} hits): {name}")
            missing += 1
    return missing


def copy_repo(scratch: pathlib.Path, index: int) -> pathlib.Path:
    work = scratch / ("repo%d" % index)
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".pytest_cache", "deploy", "artifacts", ".data", "docs"))
    return work


def main() -> None:
    source = (ROOT / CONTRACT).read_text(encoding="utf-8")
    missing = check_anchors(source)
    print(f"{len(MUTATIONS)} mutations, {missing} anchor problems")
    if "--anchors" in sys.argv:
        sys.exit(0 if missing == 0 else 1)
    only = ""
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].casefold()
    jobs = 1
    if "--jobs" in sys.argv:
        jobs = max(1, int(sys.argv[sys.argv.index("--jobs") + 1]))
    todo = [x for x in MUTATIONS if source.count(x[1]) == 1
            and (not only or any(part in x[0].casefold() for part in only.split("|")))]
    jobs = min(jobs, max(1, len(todo)))
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="grantcourt-mut-"))
    copies = [copy_repo(scratch, i) for i in range(jobs)]
    print("accept-control: unmodified copy must pass ...", flush=True)
    if not run_suite(copies[0]):
        print("CONTROL FAILED: the unmodified suite does not pass; aborting")
        shutil.rmtree(scratch, ignore_errors=True)
        sys.exit(1)
    print(f"control green; {len(todo)} mutations over {jobs} job(s)\n", flush=True)
    results = [None] * len(todo)
    cursor = [0]
    done = [0]
    lock = threading.Lock()

    def worker(work: pathlib.Path) -> None:
        target = work / CONTRACT
        while True:
            with lock:
                i = cursor[0]
                if i >= len(todo):
                    return
                cursor[0] = i + 1
            name, old, new = todo[i]
            target.write_text(source.replace(old, new), encoding="utf-8", newline="\n")
            passed = run_suite(work)
            target.write_text(source, encoding="utf-8", newline="\n")
            with lock:
                results[i] = passed
                done[0] += 1
                print(f"  [{done[0]}/{len(todo)}] {'SURVIVED' if passed else 'killed  '}: "
                      f"{name}", flush=True)

    threads = [threading.Thread(target=worker, args=(w,)) for w in copies]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    shutil.rmtree(scratch, ignore_errors=True)
    print()
    killed = survived = 0
    for (name, _old, _new), passed in zip(todo, results):
        print(("SURVIVED: " if passed else "killed:   ") + name)
        survived += 1 if passed else 0
        killed += 0 if passed else 1
    print(f"\nmutations: {killed} killed, {survived} survived, {missing} anchor missing")
    sys.exit(0 if survived == 0 and missing == 0 else 1)


if __name__ == "__main__":
    main()
