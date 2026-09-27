#!/usr/bin/env python3
"""Send the appeal the letter's proof needs, on a submission that already stands
EVALUATED, and record the transaction.

    python scripts/letter_appeal.py <address> <submission_id> --case HK06 \\
        --raw-base <pinned raw url>

The appeal appends the case's appeal items - hash-bound, fetched under consensus
like any other evidence - so the submission's item list grows and the commitment
over it must move with it. `scripts/letter_proof.py` then checks that it did.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import studionet_transport  # noqa: E402,F401 - retries RPC transport failures
from genlayer_py import create_account, create_client  # noqa: E402
from genlayer_py.chains import studionet  # noqa: E402
from genlayer_py.types import TransactionStatus  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RPC = "https://studio.genlayer.com/api"
FIXTURES = ROOT / "fixtures"


def cases() -> dict:
    out = {}
    for name in ("hackathon_submissions", "builder_grant_milestones",
                 "contribution_submissions", "adversarial_submissions"):
        path = FIXTURES / (name + ".json")
        if path.exists():
            for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
                out[case["case_id"]] = case
    return out


def digest_of(relative: str) -> str:
    return hashlib.sha256((FIXTURES / relative).read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("submission_id")
    parser.add_argument("--case", required=True)
    parser.add_argument("--raw-base", required=True)
    args = parser.parse_args()

    case = cases()[args.case]
    keys = json.loads((ROOT / ".data" / "demo_wallets.json").read_text(encoding="utf-8"))
    account = create_account(account_private_key=keys[case["applicant"]])
    client = create_client(chain=studionet, account=account, endpoint=RPC)

    items = [{"category": category,
              "url": args.raw_base + "sources/" + relative,
              "sha256": digest_of("sources/" + relative),
              "label": label}
             for relative, category, label in case["appeal_items"]]
    print("appealing", args.submission_id, "with", len(items), "new items")

    tx = client.write_contract(address=args.address, function_name="appeal",
                               args=[args.submission_id, case["appeal_reason"],
                                     json.dumps(items)])
    tx = tx if isinstance(tx, str) else "0x" + bytes(tx).hex()
    print("appeal tx", tx, flush=True)
    receipt = client.wait_for_transaction_receipt(
        transaction_hash=tx, status=TransactionStatus.FINALIZED, interval=5000, retries=300)
    leader = (receipt.get("consensus_data") or {}).get("leader_receipt") or {}
    if isinstance(leader, list):
        leader = leader[0] if leader else {}
    result = leader.get("execution_result")
    print("status", receipt.get("status"), "leader", result)
    record = {"contract": args.address, "submission_id": args.submission_id,
              "case": args.case, "appeal_tx": tx, "leader_execution": str(result),
              "added_items": items,
              "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    path = ROOT / "deploy" / ("letter_appeal_" + args.address[:10].lower() + ".json")
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")
    print("recorded", path.relative_to(ROOT))
    if str(result) != "SUCCESS":
        print(json.dumps(leader.get("result"))[:400])
        sys.exit(1)


if __name__ == "__main__":
    main()
