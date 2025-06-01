from enum import StrEnum, auto
from typing import Protocol, Callable, Any


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster


class Step(Protocol):
    parsed_lines: list[str]

    @property
    def name(self) -> str: ...
    def parse(self, line: str): ...
    @property
    def residuals(self) -> dict[str, tuple[float, ...]]: ...
    @property
    def tabular_data(self) -> dict[str, tuple[Any, ...]]: ...


class DynamicStep:
    def __init__(self, fenster: "Hauptfenster", number: int) -> None:
        self.fenster = fenster
        self.number = number
        self.increments: list[dict[str, float | int | str]] = []
        self.parsed_lines: list[str] = []
        self._residuals: dict[str, list[float]] = {}

    @property
    def name(self) -> str:
        return f"DynamicStep {self.number}"

    @property
    def cur_increment(self):
        return self.increments[-1]

    @property
    def residuals(self) -> dict[str, tuple[float, ...]]:
        return {key: tuple(value) for key, value in self._residuals.items()}

    @property
    def tabular_data(self) -> dict[str, tuple[Any, ...]]:
        if not self.increments:
            return {}

        data = {key: [] for key in self.increments[0].keys()}
        for increment_data in reversed(self.increments):
            for key, value in increment_data.items():
                data[key].append(value)

        return {key: tuple(value) for key, value in data.items()}

    def parse(self, line: str):
        if line.startswith("actual total time="):
            total_time = float(line.partition("=")[-1])
            self.increments.append(
                {"Increment #": len(self.increments) + 1, "Total time": total_time}
            )
            self.fenster.update_solver_status()

        searchwords = (
            "internal energy",
            "kinetic energy",
            "elastic contact energy",
            "energy lost due to friction",
            "total energy",
        )
        for searchword in searchwords:
            if line.startswith(searchword):
                _, _, wert = line.partition("=")
                wert = float(wert)
                try:
                    self._residuals[searchword].append(wert)
                except KeyError:
                    self._residuals[searchword] = [wert]
