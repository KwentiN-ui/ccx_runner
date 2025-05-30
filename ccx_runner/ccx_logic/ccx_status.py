import re
from ccx_runner.ccx_logic.step import Step, StepType
from ccx_runner.ccx_logic.increment import Increment
from ccx_runner.ccx_logic.iteration import Iteration
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

        # NEW STEP
        if line.startswith("STEP"):
            stripped = line.removeprefix("STEP").strip()
            number = int(stripped)
            self.steps.append(Step(number, StepType.Static))

        # INCREMENT DATA
        # new increment
        if line.startswith("increment") and "attempt" in line:
            # Get the increment number and attempt number using regex
            re_match = re.search("increment (\\d+) attempt (\\d+)", line)
            if re_match:
                increment_number = int(re_match.group(1))
                attempt = int(re_match.group(2))
                self.steps[-1].increments.append(
                    Increment(self.steps[-1], increment_number, attempt)
                )

        # increment size
        if "increment size=" in line:
            size = float(line.partition("=")[-1])
            self.steps[-1].increments[-1].incremental_time = size

        if "actual total time=" in line:
            total_time = float(line.partition("=")[-1])
            self.steps[-1].increments[-1].total_time = total_time

        # ITERATION DATA
        if line.startswith("iteration"):
            number = int(line.partition(" ")[-1])
            self.steps[-1].increments[-1].iterations.append(
                Iteration(self.steps[-1].increments[-1], number)
            )

        self.hauptfenster.update_solver_status()
