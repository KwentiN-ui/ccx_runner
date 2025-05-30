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
        self.parsed_lines: list[str] = []

    def parse(self, line: str):
        line = line.strip()

        # NEW STEP
        if line.endswith("was selected"):
            typ_str = line.partition("was")[0].strip()
            typ = None
            if typ_str == "Static analysis":
                typ = StepType.Static
            if typ_str == "Dynamic analysis":
                typ = StepType.Dynamic
            if typ:
                stripped = line.removeprefix("STEP").strip()
                number = len(self.steps) + 1
                self.steps.append(Step(number, typ))

        if self.steps and self.steps[-1].type == StepType.Static:
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
                if self.steps[-1].increments:
                    self.steps[-1].increments[-1].incremental_time = size

            if "actual total time=" in line:
                total_time = float(line.partition("=")[-1])
                if self.steps[-1].increments:
                    self.steps[-1].increments[-1].total_time = total_time

            # ITERATION DATA
            if line.startswith("iteration"):
                number = int(line.partition(" ")[-1])
                if self.steps[-1].increments:
                    self.steps[-1].increments[-1].iterations.append(
                        Iteration(self.steps[-1].increments[-1], number)
                    )
            
            # look for Iteration Residuals
            if ("convergence" in line) or ("no convergence" in line):
                iteration = self.steps[-1].increments[-1].iterations[-1]

                for prev_line in self.parsed_lines[-2::-1]:
                    # gehe Rückwärts bis du eine leere Zeile findest
                    if len(prev_line.strip()) == 0: # leere Zeile
                        break # out of for loop
                    else:
                        name,_,wert = prev_line.partition("=")
                        iteration.data[name] = float(wert.strip().partition(" ")[0])
            
        self.parsed_lines.append(line)
        self.hauptfenster.update_solver_status()
