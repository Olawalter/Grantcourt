# Verdictbox contract (excerpt)

class Verdictbox(gl.Contract):
    verdicts: TreeMap[str, str]

    @gl.public.write
    def judge(self, job_id: str, brief: str, delivery: str) -> None:
        def leader():
            return gl.nondet.exec_prompt(MATCH_PROMPT + brief + delivery, response_format="json")

        def validator(result) -> bool:
            return leader()["matches"] == result.calldata["matches"]

        self.verdicts[job_id] = json.dumps(gl.vm.run_nondet_unsafe(leader, validator))
