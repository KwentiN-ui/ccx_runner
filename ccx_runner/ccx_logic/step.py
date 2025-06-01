import re
from enum import StrEnum, auto
from typing import Protocol, Callable, Any

from ccx_runner.ccx_logic.increment import Increment
from ccx_runner.ccx_logic.iteration import Iteration

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster


class Step(Protocol):
    increments: list[Increment]
    parsed_lines: list[str]

    @property
    def name(self) -> str: ...
    @property
    def cur_increment(self) -> Increment: ...
    @property
    def cur_iteration(self) -> Iteration: ...
    def parse(self, line: str): ...
    @property
    def residuals(self) -> dict[str, tuple[float, ...]]: ...
    @property
    def tabular_data(self) -> dict[str, tuple[Any]]: ...


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
    def tabular_data(self) -> dict[str, tuple[Any]]:
        return {}

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


class DynamicStep:
    def __init__(self, fenster: "Hauptfenster", number: int) -> None:
        self.fenster = fenster
        self.number = number
        self.increments: list[Increment] = []
        self.parsed_lines: list[str] = []
        self._residuals: dict[str, list[float]] = {}

    @property
    def name(self) -> str:
        return f"DynamicStep {self.number}"

    @property
    def cur_increment(self):
        return self.increments[-1]

    @property
    def cur_iteration(self):
        return self.cur_increment.iterations[-1]

    @property
    def residuals(self) -> dict[str, tuple[float, ...]]:
        return {key: tuple(value) for key, value in self._residuals.items()}

    @property
    def tabular_data(self) -> dict[str, tuple[Any]]:
        return {}

    def parse(self, line: str):
        if line.startswith("actual total time="):
            self.increments.append(Increment(self, len(self.increments) + 1, 0))
            self.fenster.update_solver_status()


class FrequencyStep:
    def __init__(
        self, fenster: "Hauptfenster", number: int, update_call: Callable
    ) -> None:
        self.fenster = fenster
        self.number = number
        self.increments: list[Increment] = []
        self.parsed_lines: list[str] = []

    @property
    def name(self) -> str:
        return f"DynamicStep {self.number}"

    @property
    def cur_increment(self):
        return self.increments[-1]

    @property
    def cur_iteration(self):
        return self.cur_increment.iterations[-1]

    def parse(self, line: str):
        pass
