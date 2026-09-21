# Hypeboard contract (excerpt)

class Hypeboard(gl.Contract):
    scores: TreeMap[str, u256]

    @gl.public.write
    def bump(self, project: str) -> None:
        self.scores[project] = self.scores.get(project, u256(0)) + u256(1)
