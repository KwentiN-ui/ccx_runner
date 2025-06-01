from ccx_runner.ccx_logic.static.increment import Increment
from ccx_runner.ccx_logic.static.iteration import Iteration
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster


import re
from typing import Any


class StaticStep:
    def __init__(self, fenster: "Hauptfenster", number: int) -> None:
        self.fenster = fenster
        self.number = number
        self.parsed_lines: list[str] = []
        self.increments: list[Increment] = []

    @property
    def name(self) -> str:
        return f"StaticStep {self.number}"

    @property
    def cur_increment(self):
        return self.increments[-1]

    @property
    def cur_iteration(self):
        return self.cur_increment.iterations[-1]

    @property
    def tabular_data(self) -> dict[str, tuple[Any, ...]]:
        data: dict[str, tuple[Any, ...]] = {
            "Increment #": tuple(inc.number for inc in reversed(self.increments)),
            "Attempt": tuple(inc.attempt for inc in reversed(self.increments)),
            "Iterations #": tuple(
                len(inc.iterations) for inc in reversed(self.increments)
            ),
            "delta Time": tuple(
                inc.incremental_time for inc in reversed(self.increments)
            ),
            "total Time": tuple(inc.total_time for inc in reversed(self.increments)),
        }
        return data

    @property
    def residuals(self) -> dict[str, tuple[float, ...]]:
        if self.increments:
            return self.increments[-1].residuals
        else:
            return {}

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
            self.fenster.update_solver_status()
            number = int(line.partition(" ")[-1])
            if self.increments:
                self.increments[-1].iterations.append(
                    Iteration(self.increments[-1], number)
                )

        # Residuals of the iteration
        searchwords = (
            "average force",
            "time avg. forc",
            "largest residual force",
            "largest increment of disp",
            "largest correction to disp",
        )
        for searchword in searchwords:
            if line.startswith(searchword) and "=" in line:
                value = float(line.split(" ")[-1])
                self.cur_iteration.data[searchword] = value

        self.parsed_lines.append(line)
