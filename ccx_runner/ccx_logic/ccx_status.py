from ccx_runner.ccx_logic.step import Step


class CalculixStatus:
    def __init__(self) -> None:
        self.running = False
        self.steps: list[Step] = []

    def parse(self, line: str):
        pass
