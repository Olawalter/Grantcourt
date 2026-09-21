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

DEPLOY_RECORD_PENDING
