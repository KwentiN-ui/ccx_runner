import re
from ccx_runner.ccx_logic.step import Step, StaticStep, DynamicStep
from ccx_runner.ccx_logic.static.increment import Increment
from ccx_runner.ccx_logic.static.iteration import Iteration
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster


class CalculixStatus:
    def __init__(self, hauptfenster: "Hauptfenster") -> None:
        self.hauptfenster = hauptfenster
        self.running = False
        self.steps: list[Step] = []

    def parse(self, line: str):
        line = line.strip()

        # check if a new STEP was found first
        if line.endswith("was selected"):
            typ_str = line.partition("was")[0].strip()
            step = None
            if typ_str == "Static analysis":
                step = StaticStep
            if typ_str == "Dynamic analysis":
                step = DynamicStep
            if step:
                number = len(self.steps) + 1
                self.steps.append(step(self.hauptfenster, number))

        # relay the line to the corresponding step
        if self.steps:
            self.steps[-1].parse(line)
        else:
            # parse the preamble
            pass
