# Tallyhall contract (excerpt)

class Tallyhall(gl.Contract):
    outcomes: TreeMap[str, str]

    @gl.public.write
    def judge(self, proposal_id: str, goal: str, evidence: str) -> None:
        def leader():
            return gl.nondet.exec_prompt(GOAL_PROMPT + goal + evidence, response_format="json")

        def validator(result) -> bool:
            return leader()["met"] == result.calldata["met"]

        self.outcomes[proposal_id] = json.dumps(gl.vm.run_nondet_unsafe(leader, validator))
