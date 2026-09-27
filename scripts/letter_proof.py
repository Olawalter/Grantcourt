#!/usr/bin/env python3
"""Prove the letter's fix on chain: after an appeal appends evidence, every
commitment the contract returns describes the list printed beside it.

    python scripts/letter_proof.py <address> --submission GS-000001

Reads only. It asserts, against the deployment, that

  * get_submission's `evidence_commitment` is the sha256 of the canonical JSON
    of the `items` in the same answer, and that `evidence_digests` is that
    list's digests in order;
  * `filed_evidence_commitment` is the commitment the FIRST evaluation record
    carries - the list as filed;
  * the appeal round's own record carries the commitment of the expanded list;
  * `evidence_appended_by_appeal` and `item_count` agree with the lists.

The outcome is written to deploy/letter_proof_<address>.json.
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

ROOT = pathlib.Path(__file__).resolve().parents[1]
RPC = "https://studio.genlayer.com/api"


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    parser.add_argument("--submission", required=True)
    args = parser.parse_args()

    client = create_client(chain=studionet, account=create_account(), endpoint=RPC)

    def read(method: str, params):
        return client.read_contract(address=args.address, function_name=method, args=params)

    submission = read("get_submission", [args.submission])
    if not submission.get("found"):
        sys.exit("no such submission on that contract")
    records = [read("get_evaluation_record", [eid])
               for eid in submission["evaluation_ids"]]

    checks = []

    def check(name: str, ok: bool, detail: str = ""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(("PASS  " if ok else "FAIL  ") + name + ("  -> " + detail if detail else ""))

    items = submission["items"]
    current = sha256_hex(canonical(items))
    check("get_submission's commitment is over the items it returns",
          submission["evidence_commitment"] == current,
          submission["evidence_commitment"] + " vs " + current)
    check("the digests it returns are those items' digests, in order",
          submission["evidence_digests"] == [it["sha256"] for it in items])
    check("item_count is the length of that list",
          submission["item_count"] == len(items), str(submission["item_count"]))
    check("more than one round was judged", len(records) > 1,
          ", ".join(submission["evaluation_ids"]))
    if len(records) > 1:
        first, last = records[0], records[-1]
        check("the filed commitment is the first round's commitment",
              submission["filed_evidence_commitment"] == first["evidence_commitment"],
              submission["filed_evidence_commitment"] + " vs "
              + first["evidence_commitment"])
        check("the appeal appended evidence",
              len(last["items"]) > len(first["items"]),
              str(len(first["items"])) + " -> " + str(len(last["items"])))
        check("evidence_appended_by_appeal says so",
              submission["evidence_appended_by_appeal"] is True)
        check("the current commitment is the appeal round's commitment",
              submission["evidence_commitment"] == last["evidence_commitment"])
        check("the two commitments differ, as the two lists do",
              submission["evidence_commitment"]
              != submission["filed_evidence_commitment"])
        for record in records:
            check("round " + record["evaluation_id"] + " carries the commitment of the "
                  "list it read",
                  record["evidence_commitment"] == sha256_hex(canonical(record["items"])))

    out = {
        "contract": args.address, "submission_id": args.submission,
        "read_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluation_ids": submission["evaluation_ids"],
        "filed_evidence_commitment": submission["filed_evidence_commitment"],
        "evidence_commitment": submission["evidence_commitment"],
        "evidence_appended_by_appeal": submission["evidence_appended_by_appeal"],
        "item_count": submission["item_count"],
        "items": [{"evidence_id": it["evidence_id"], "sha256": it["sha256"]}
                  for it in items],
        "rounds": [{"evaluation_id": r["evaluation_id"], "mode": r.get("mode", ""),
                    "items": len(r["items"]),
                    "evidence_commitment": r["evidence_commitment"]} for r in records],
        "checks": checks,
        "passed": all(c["ok"] for c in checks),
    }
    path = ROOT / "deploy" / ("letter_proof_" + args.address[:10].lower() + ".json")
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")
    print(("all " + str(len(checks)) + " checks passed" if out["passed"]
           else "CHECKS FAILED") + "; wrote " + str(path.relative_to(ROOT)))
    if not out["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
