from ccx_runner.ccx_logic.step import Step, StepType
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster

class CalculixStatus:
    def __init__(self, hauptfenster:"Hauptfenster") -> None:
        self.hauptfenster = hauptfenster
        self.running = False
        self.steps: list[Step] = []

    def parse(self, line: str):
        line = line.strip()
        if line.startswith("STEP"):
            stripped = line.removeprefix("STEP").strip()
            number = int(stripped)
            self.steps.append(Step(number, StepType.Static))

        self.hauptfenster.update_solver_status()
