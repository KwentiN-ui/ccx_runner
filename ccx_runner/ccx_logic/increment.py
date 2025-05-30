from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.ccx_logic.step import Step
    from ccx_runner.ccx_logic.iteration import Iteration


class Increment:
    def __init__(self, step: "Step", number: int, attempt: int) -> None:
        self.step = step
        self.number = number
        self.attempt = attempt
        self.total_time: float | None = None
        self.incremental_time: float | None = None
        self.iterations: list[Iteration] = []

    @property
    def name(self) -> str:
        return f"Increment {self.number} attempt {self.attempt}"
