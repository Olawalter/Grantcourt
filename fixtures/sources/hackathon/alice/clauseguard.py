# Clauseguard contract (excerpt)

class Clauseguard(gl.Contract):
    verdicts: TreeMap[str, str]

    @gl.public.write
    def judge_clause(self, clause_id: str, clause: str) -> None:
        def leader():
            answer = gl.nondet.exec_prompt(PROMPT + clause, response_format="json")
            return answer["verdict"]

        def validator(result) -> bool:
            return result.calldata == leader()

        # every validator re-reads the clause with its own model and must reach
        # the same verdict: UNFAIR, FAIR or UNCLEAR
        self.verdicts[clause_id] = gl.vm.run_nondet_unsafe(leader, validator)
