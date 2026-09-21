"""StudioNet integration: the deployment of record in deploy/deployment.json,
checked over the network.

    python -m pytest tests/integration -v
    GRANTCOURT_LIVE_WRITES=1 python -m pytest tests/integration -v

Read-only by default: the deployed source is byte-identical to
contracts/grantcourt.py, the deployed schema exposes every public method in
that file, the views answer, the contract's balance is exactly what it says it
holds, and what the live run recorded reads back - records, receipts and
constitution hashes. With GRANTCOURT_LIVE_WRITES=1 one write goes through real
consensus: a fresh wallet creates a draft program (StudioNet is gasless; the
draft holds no funds).

genlayer-py is used directly: gltest's ContractFactory cannot bind a hosted
contract from its schema on this SDK generation.
"""

import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "grantcourt.py"
RECORD = ROOT / "deploy" / "deployment.json"
TRANSCRIPT = ROOT / "deploy" / "live_run_transcript.json"
PROGRAMS = ROOT / "fixtures" / "programs.json"
RPC = "https://studio.genlayer.com/api"

pytestmark = pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded")
sys.path.insert(0, str(ROOT / "scripts"))


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for attempt in range(6):
        try:
            request = urllib.request.Request(RPC, data=body, headers={
                "Content-Type": "application/json", "User-Agent": "grantcourt-integration"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode())
        except Exception as err:          # noqa: BLE001 - transport errors vary
            last = err
            time.sleep(10 * (attempt + 1))
    raise last


@pytest.fixture(scope="module")
def deployment():
    return json.loads(RECORD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client():
    import studionet_transport  # noqa: F401
    from genlayer_py import create_account, create_client
    from genlayer_py.chains import studionet
    return create_client(chain=studionet, account=create_account())


@pytest.fixture(scope="module")
def read(deployment, client):
    return lambda fn, args: client.read_contract(
        address=deployment["contract_address"], function_name=fn, args=args)


@pytest.fixture(scope="module")
def transcript(deployment):
    if not TRANSCRIPT.exists():
        pytest.skip("no live run recorded")
    data = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    if data.get("address", "").lower() != deployment["contract_address"].lower():
        pytest.skip("the transcript belongs to another deployment")
    return data


def test_deployed_source_is_the_committed_file(deployment):
    result = rpc("gen_getContractCode", [deployment["contract_address"]])["result"]
    deployed = result.encode() if result.lstrip().startswith("#") else base64.b64decode(result)
    local = CONTRACT.read_bytes()
    assert hashlib.sha256(deployed).hexdigest() == hashlib.sha256(local).hexdigest() \
        == deployment["source_sha256"]


def test_deployed_schema_exposes_every_public_method(deployment):
    schema = rpc("gen_getContractSchema", [deployment["contract_address"]])["result"]
    methods = set(schema["methods"])
    declared = re.findall(r"@gl\.public\.(?:view|write(?:\.payable)?)\n    def (\w+)\(",
                          CONTRACT.read_text(encoding="utf-8"))
    assert len(declared) == 31
    assert set(declared) <= methods, sorted(set(declared) - methods)


def test_views_answer(read):
    config = read("get_config", [])
    assert config["contract_version"] == "0.1.0" and config["receipt_version"] == 1
    assert len(config["evaluation_statuses"]) == 7 and len(config["reason_codes"]) == 21
    assert read("get_submission", ["GS-999999"])["found"] is False
    assert read("is_rewardable", ["GS-999999"])["rewardable"] is False


def test_the_balance_is_exactly_what_the_contract_holds(deployment, client, read):
    stats = read("get_stats", [])
    held = int(stats["pools_atto"]) + int(stats["bonds_atto"]) + int(stats["claimable_atto"])
    assert int(stats["held_atto"]) == held
    assert client.get_balance(deployment["contract_address"]) == held


def test_the_live_outcomes_read_back(read, transcript):
    outcomes = transcript["outcomes"]
    assert outcomes
    for key, row in outcomes.items():
        record = read("get_evaluation_record", [row["evaluation_id"]])
        assert [record["status"], record["reason_code"], record["score_band"]] == \
            row["observed"], key
        assert record["record_digest"] == row["record_digest"], key
        assert record["criterion_result_hash"] == row["criterion_result_hash"], key


def test_every_constitution_hash_recomputes(read, transcript):
    for key, program_id in transcript["programs"].items():
        view = read("get_program_definition_hash", [program_id])
        assert view["definition_hash"] == view["recomputed_hash"], key


def test_settled_submissions_are_final_and_their_receipts_stand(read, transcript):
    for key, row in transcript.get("settled", {}).items():
        sid = transcript["submissions"][key]
        state = read("is_rewardable", [sid])
        assert state["final"] is True, key
        assert read("get_reward_entitlement", [sid])["entitled_atto"] == row["reward_atto"], key
        receipt = read("get_latest_receipt", [sid])
        assert receipt["final"] is True, key
        assert receipt["criterion_result_hash"] == row["receipt"]["criterion_result_hash"], key


@pytest.mark.skipif(os.environ.get("GRANTCOURT_LIVE_WRITES") != "1",
                    reason="writes to the deployment of record are opt-in")
def test_a_write_through_consensus(deployment):
    import studionet_transport  # noqa: F401
    from genlayer_py import create_account, create_client
    from genlayer_py.chains import studionet
    from genlayer_py.types import TransactionStatus
    writer = create_client(chain=studionet, account=create_account())
    spec = json.loads(PROGRAMS.read_text(encoding="utf-8"))["programs"]["hackathon"]
    for ref in spec["reference_sources"]:
        ref["url"] = ref["url"].replace("{BASE}", "https://sources.example.org/integration/")
    spec["title"] = "Integration test draft"
    before = writer.read_contract(address=deployment["contract_address"],
                                  function_name="list_programs", args=[0, 1])["total"]
    tx = writer.write_contract(address=deployment["contract_address"],
                               function_name="create_program", args=[json.dumps(spec)],
                               consensus_max_rotations=3)
    receipt = writer.wait_for_transaction_receipt(
        transaction_hash=tx, status=TransactionStatus.FINALIZED, interval=5000, retries=240)
    leader = receipt["consensus_data"]["leader_receipt"]
    assert str((leader[0] if isinstance(leader, list) else leader)["execution_result"]) == \
        "SUCCESS"
    after = writer.read_contract(address=deployment["contract_address"],
                                 function_name="list_programs", args=[0, 1])["total"]
    assert after == before + 1
