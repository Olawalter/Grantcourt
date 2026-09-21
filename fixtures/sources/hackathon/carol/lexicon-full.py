# Lexicon contract (excerpt, complete)

class Lexicon(gl.Contract):
    verdicts: TreeMap[str, str]

    @gl.public.write
    def judge(self, item_id: str, source: str, translation: str) -> None:
        def leader():
            return gl.nondet.exec_prompt(FAITHFUL_PROMPT + source + translation,
                                         response_format="json")

        def validator(result) -> bool:
            # the faithfulness verdict must match; the explanation may differ
            return leader()["faithful"] == result.calldata["faithful"]

        self.verdicts[item_id] = json.dumps(gl.vm.run_nondet_unsafe(leader, validator))
