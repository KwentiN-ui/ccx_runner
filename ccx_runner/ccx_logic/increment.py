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

    @property
    def residuals(self):
        resid: dict[str, tuple[float,...]] = {}
        if self.iterations:
            keys = tuple(self.iterations[0].data.keys())
            for key in keys:
                resid[key] = tuple(iteration.data.get(key,0) for iteration in self.iterations)
        return resid
