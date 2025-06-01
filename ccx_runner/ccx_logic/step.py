import re
from enum import StrEnum, auto
from typing import Protocol

from ccx_runner.ccx_logic.increment import Increment
from ccx_runner.ccx_logic.iteration import Iteration

class Step(Protocol):
    increments: list[Increment]
    @property
    def name(self) -> str: ...
    def parse(self, line:str): ...

class StaticStep:
    def __init__(self, number: int) -> None:
        self.number = number
        self.parsed_lines: list[str] = []
        self.increments: list[Increment] = []

    @property
    def name(self) -> str:
        return f"StaticStep {self.number}"

    def parse(self, line: str):
        # INCREMENT DATA
        # new increment
        if line.startswith("increment") and "attempt" in line:
            # Get the increment number and attempt number using regex
            re_match = re.search("increment (\\d+) attempt (\\d+)", line)
            if re_match:
                increment_number = int(re_match.group(1))
                attempt = int(re_match.group(2))
                self.increments.append(Increment(self, increment_number, attempt))

        # increment size
        if "increment size=" in line:
            size = float(line.partition("=")[-1])
            if self.increments:
                self.increments[-1].incremental_time = size

        if "actual total time=" in line:
            total_time = float(line.partition("=")[-1])
            if self.increments:
                self.increments[-1].total_time = total_time

        # ITERATION DATA
        if line.startswith("iteration"):
            number = int(line.partition(" ")[-1])
            if self.increments:
                self.increments[-1].iterations.append(
                    Iteration(self.increments[-1], number)
                )

        # look for Iteration Residuals
        if ("convergence" in line) or ("no convergence" in line):
            iteration = self.increments[-1].iterations[-1]

            for prev_line in self.parsed_lines[-2::-1]:
                # gehe Rückwärts bis du eine leere Zeile findest
                if len(prev_line.strip()) == 0:  # leere Zeile
                    break  # out of for loop
                else:
                    name, _, wert = prev_line.partition("=")
                    iteration.data[name] = float(wert.strip().partition(" ")[0])

        self.parsed_lines.append(line)

class DynamicStep:
    def __init__(self, number: int) -> None:
        self.number = number
        self.increments: list[Increment] = []

    @property
    def name(self) -> str:
        return f"DynamicStep {self.number}"

    def parse(self, line: str):
        pass
