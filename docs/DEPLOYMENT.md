# Deployment

The workflow, then only facts a receipt, a read or a command output shows.
Every recorded value is in `deploy/deployment.json`, written by
`scripts/deploy_studionet.py`.

## Assumptions

| Item | Value |
|---|---|
| Network | GenLayer StudioNet, chain id 61999, RPC `https://studio.genlayer.com/api`, explorer `https://explorer-studio.genlayer.com` |
| Gas | StudioNet is gasless; a deployer holding 0 GEN can deploy and write |
| Wallets | the deployer key is created on first use in `.data/deployer.json`; the demo wallets' keys are in `.data/demo_wallets.json` (`scripts/make_wallets.py`); `.data/` is gitignored and no key is ever printed |
| Environment variables | none are required. `GENVM_VERSION=v0.3.0-rc7` pins the linter and the test runner when other GenVM bundles are cached; `GRANTCOURT_LIVE_WRITES=1` opts the integration suite into one write |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Evidence hosting | a live run serves `fixtures/` from a commit-pinned `raw.githubusercontent.com` URL, so every validator fetches exactly the committed bytes |

## Workflow

Build and validate (the contract is one Python file; there is no build step
beyond the checks):

```bash
pip install -r requirements-test.txt
```

```bash
python scripts/fetch_genvm_bundle.py
```

```bash
genvm-lint check contracts/grantcourt.py --json
```

```bash
python -m pytest tests/direct -q
```

Deploy and capture the address - the script refuses an uncommitted, non-ASCII
or CR-bearing contract, waits for FINALIZED, requires leader execution
SUCCESS, reads the deployed source back with `gen_getContractCode` and writes
`deploy/deployment.json` only after the byte comparison:

```bash
python scripts/deploy_studionet.py
```

Post-deployment check:

```bash
python scripts/deploy_studionet.py --verify
```

```bash
python -m pytest tests/integration -q
```

Sample program, submission, evaluation, receipt and appeal - the live run does
all of them with real transactions, reading evidence from a pinned commit:

```bash
python scripts/live_run.py <address> --raw-base https://raw.githubusercontent.com/<owner>/<repo>/<commit>/fixtures/ --phase full
```

By hand, with any GenLayer client: `create_program(constitution_json)` with a
constitution from `fixtures/programs.json` (replace `{BASE}` with the raw
base), `fund_program(program_id)` with value, `activate_program(program_id)`;
then `submit(program_id, definition_hash, ...)` with the bond,
`request_evaluation(submission_id)`, `get_latest_receipt(submission_id)`,
optionally `appeal(submission_id, reason, items_json)`, and after the window
`finalize_submission(submission_id)` and `withdraw()`.

## Deployment of record

| Item | Value |
|---|---|
| Network | GenLayer StudioNet, chain id 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | `0x89310fcbA7155d99826934E4e75c273F8f11D709` |
| Explorer | https://explorer-studio.genlayer.com/address/0x89310fcbA7155d99826934E4e75c273F8f11D709 |
| Deployment transaction | `0x8741cd475b0d4832c16ce1643e20558f9bbd9dbdc0d8d46969cc135a837d2e23` |
| Deployed at | 2026-09-21T19:47:41Z |
| Receipt | status FINALIZED, leader execution SUCCESS, votes AGREE, AGREE, AGREE, AGREE, AGREE |
| Source commit | `527c0ebfda9bc7313d0e48544955d550c9baacda` |
| Source blob | `adc52e78c9199482972e0f172cb995972e426ac4` |
| Source sha256 | `38e42cc1b39f0c809cf3b50de9bd5623889956b30acf4ff8130d520fb54a27e9` |
| Deployed source sha256 (`gen_getContractCode`) | `38e42cc1b39f0c809cf3b50de9bd5623889956b30acf4ff8130d520fb54a27e9` - byte-identical |
| Deployer (public address) | `0x85a6304356e9d4970e2F8C4Fd44AeFaA3B8682C1` |
| Runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |

`python scripts/deploy_studionet.py --verify`: deployed and repository sha256 equal, byte-identical, 31 schema methods.

## Toolchain

| Tool | Version |
|---|---|
| Python | 3.12.2 |
| genlayer-py | 0.16.3 |
| genlayer-test (Direct Mode) | 0.29.2 |
| genvm-linter | 0.11.0, GenVM bundle v0.3.0-rc7 |

`genvm-lint check contracts/grantcourt.py --json`: lint ok (3 checks), validation ok, 31 methods (20 view, 11 write). One notice, I200: a newer py-genlayer runner (`1zr6nqk5...`) is available. The contract stays on the runner this repository has deployed and run live; the newer runner was not tested here.

## Disposable diagnostic deployments

| Address | Source commit | Purpose | Record |
|---|---|---|---|
| `0xEd3e3806DaA012e73C709fDe0045aDf0dDa96E89` | `f963d6f` | diagnostic pass 1: every catalogue case evaluated once, per-node readings recorded | `deploy/diagnostics/deployment_0xed3e3806.json`, `cases_0xed3e3806.json` |
| `0x27674f329564F6cBC7f808a2A61a455aeC34eaEE` | `e979504` | diagnostic pass 2: the five cases pass 1 missed, after the prompt changes | `deploy/diagnostics/deployment_0x27674f32.json`, `cases_0x27674f32.json`, `cases_0x27674f32_hk06.json` |

Neither is the deployment of record. What they showed and what changed in response: [`CONSENSUS.md`](CONSENSUS.md#live-diagnostic-findings). After pass 2 a fresh-reader audit of the contract found five defects, all fixed before the deployment of record; see [`SECURITY.md`](SECURITY.md) and `SUBMISSION.md`.

## Live run

| Item | Value |
|---|---|
| Transcript | `deploy/live_run_transcript.json`, log `deploy/live_run.log` |
| Transactions | 115, no rejected round |
| Window | 2026-09-21T19:48:19Z to 2026-09-21T21:46:27Z |
| Fixtures served from | `https://raw.githubusercontent.com/Olawalter/Grantcourt/2b9f427/fixtures/` |
| Outcomes held | 20 of 24 |
| Ledger at the end | chain balance 107500000000000000 atto = accounted 107500000000000000 atto |

Integration against the deployment (`python -m pytest tests/integration -q`): 7 passed, 1 skipped (the opt-in live write). One earlier run hit StudioNet's 30-reads-a-minute limit (`-32029`) on two checks; `scripts/studionet_transport.py` now retries that code, and the full suite then passed in one run.

Results, and the plain statement of what did not hold: [`../README.md`](../README.md#verified).
