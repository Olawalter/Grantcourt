"""The happy paths and every fixture case: each catalogue case runs through
the real contract and must derive exactly the status, reason and band its
catalogue entry expects - and move exactly the money that outcome implies."""

import pytest

from tests.direct.support import (
    CASES, MILLI, POOL, answer_for, appeal_case, as_sender, assert_conserved, bond_of,
    claimable, evaluate, finalize_after_window, finding, open_program, run_case, submit,
    wallet,
)

PANEL_CASES = [c for c in sorted(CASES) if CASES[c]["answer"] is not None]
CODE_CASES = [c for c in sorted(CASES) if CASES[c]["answer"] is None]


def expect(record: dict, expected: list):
    assert [record["status"], record["reason_code"], record["score_band"]] == expected, \
        (record["status"], record["reason_code"], record["score_band"],
         record["overall_score"])


@pytest.mark.parametrize("case_id", [c for c in PANEL_CASES if not c.startswith("GM0")
                                     or c == "GM01" or c == "GM03"])
def test_panel_case_derives_its_expected_outcome(court, direct_vm, case_id):
    _sid, record = run_case(court, direct_vm, case_id)
    expect(record, CASES[case_id]["expected"])
    assert record["panel_state"] == "ASSESSED"


@pytest.mark.parametrize("case_id", CODE_CASES)
def test_code_decided_case_never_asks_the_panel(court, direct_vm, case_id):
    """The panel is not mocked: a model call would fail the round."""
    case = CASES[case_id]
    program_id = open_program(court, direct_vm, case["program"])
    sid = submit(court, direct_vm, program_id, case_id)
    record = evaluate(court, direct_vm, sid, None)
    expect(record, case["expected"])
    assert record["panel_state"] == "SKIPPED"
    assert all(f["by"] == "CODE" for f in record["criterion_results"])


def test_hackathon_pass_pays_its_band_and_returns_the_bond(court, direct_vm):
    program_id = open_program(court, direct_vm, "hackathon")
    bond = bond_of(court, program_id)
    sid = submit(court, direct_vm, program_id, "HK01")
    record = evaluate(court, direct_vm, sid, answer_for("HK01"))
    assert record["reward_atto"] == str(60 * MILLI)
    assert court.is_rewardable(sid) == {"found": True, "submission_id": sid,
                                        "rewardable": True, "final": False,
                                        "score_band": "TIER_A"}
    assert court.get_reward_entitlement(sid)["pending_atto"] == str(60 * MILLI)
    assert finalize_after_window(court, direct_vm, sid) == "REWARDED"
    assert claimable(court, "alice") == 60 * MILLI + bond
    receipt = court.get_latest_receipt(sid)
    assert receipt["final"] and receipt["final_status"] == "PASS"
    assert receipt["reward_band"] == "TIER_A" and receipt["score"] == 100
    assert receipt["policy_version"] == 1
    assert receipt["definition_hash"] == court.get_program(program_id)["definition_hash"]
    assert_conserved(court, POOL + bond)
    as_sender(direct_vm, "alice")
    assert court.withdraw() == str(60 * MILLI + bond)
    assert_conserved(court, POOL + bond, 60 * MILLI + bond)


def test_builder_grant_releases_tranches_in_order(court, direct_vm):
    program_id = open_program(court, direct_vm, "grant")
    sid1 = submit(court, direct_vm, program_id, "GM01")
    expect(evaluate(court, direct_vm, sid1, answer_for("GM01")), ["PASS", "MEETS_POLICY", "M1"])
    progress = court.get_milestone_progress(program_id, wallet("erin"))
    assert progress["passed"] == 0 and progress["open_filing"] == sid1
    with direct_vm.expect_revert("already has an open filing"):
        submit(court, direct_vm, program_id, "GM01",
               evidence_json='[{"category":"MILESTONE_REPORT","url":"https://x.example.org/r",'
                             '"sha256":"' + "a" * 64 + '","label":"again"}]')
    assert finalize_after_window(court, direct_vm, sid1) == "REWARDED"
    assert claimable(court, "erin") == 50 * MILLI
    assert court.get_milestone_progress(program_id, wallet("erin"))["next_milestone"] == "M2"
    sid2 = submit(court, direct_vm, program_id, "GM02")
    expect(evaluate(court, direct_vm, sid2, answer_for("GM02")), ["PASS", "MEETS_POLICY", "M2"])
    assert finalize_after_window(court, direct_vm, sid2) == "REWARDED"
    assert claimable(court, "erin") == 80 * MILLI
    progress = court.get_milestone_progress(program_id, wallet("erin"))
    assert progress["passed"] == 2 and progress["next_milestone"] == ""


def test_failed_milestone_frees_the_slot_and_releases_nothing(court, direct_vm):
    program_id = open_program(court, direct_vm, "grant")
    sid = submit(court, direct_vm, program_id, "GM03")
    expect(evaluate(court, direct_vm, sid, answer_for("GM03")),
           ["FAIL", "CLAIM_CONTRADICTED", "NONE"])
    assert finalize_after_window(court, direct_vm, sid) == "FINALIZED"
    assert claimable(court, "erin") == 0
    assert court.get_program(program_id)["reserved_atto"] == "0"
    progress = court.get_milestone_progress(program_id, wallet("erin"))
    assert progress["passed"] == 0 and progress["open_filing"] == ""
    sid2 = submit(court, direct_vm, program_id, "GM01")
    assert sid2 != sid


def test_contribution_pass(court, direct_vm):
    sid, record = run_case(court, direct_vm, "CT01")
    expect(record, ["PASS", "MEETS_POLICY", "FULL"])
    assert finalize_after_window(court, direct_vm, sid) == "REWARDED"
    assert claimable(court, "alice") == 25 * MILLI + 2 * MILLI


def test_appeal_with_new_evidence_passes_and_keeps_history(court, direct_vm):
    program_id = open_program(court, direct_vm, "hackathon")
    sid = submit(court, direct_vm, program_id, "HK06")
    first = evaluate(court, direct_vm, sid, answer_for("HK06"))
    expect(first, CASES["HK06"]["expected"])
    second = appeal_case(court, direct_vm, sid, "HK06")
    expect(second, CASES["HK06"]["appeal_expected"])
    assert second["appeal_of"] == first["evaluation_id"]
    assert second["evidence_scope"] == {"prior": ["E1", "E2", "E3"], "added": ["E4", "E5"]}
    assert second["deficiency"] == {"original_status": "INSUFFICIENT_EVIDENCE",
                                    "original_reason": "REQUIRED_CRITERION_INSUFFICIENT",
                                    "resolved": True}
    assert court.get_evaluation_record(first["evaluation_id"])["status"] == \
        "INSUFFICIENT_EVIDENCE"
    assert court.get_appeal_state(sid)["appeals_remaining"] == 0
    assert finding(second, "implementation")["state"] == "MET"
    as_sender(direct_vm, "stranger")
    assert court.finalize_submission(sid) == "REWARDED"
    assert court.get_latest_receipt(sid)["appeal_count"] == 1
