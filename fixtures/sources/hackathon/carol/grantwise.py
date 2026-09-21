# Grantwise contract (excerpt)

class Grantwise(gl.Contract):
    reviews: TreeMap[str, str]

    @gl.public.write
    def review(self, proposal_id: str, proposal: str) -> None:
        def leader():
            return gl.nondet.exec_prompt(REVIEW_PROMPT + proposal, response_format="json")

        def validator(result) -> bool:
            mine = leader()
            # the per-question verdicts must match; the explanations may differ
            return mine["verdicts"] == result.calldata["verdicts"]

        self.reviews[proposal_id] = json.dumps(gl.vm.run_nondet_unsafe(leader, validator))
