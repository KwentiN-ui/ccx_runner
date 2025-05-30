from enum import StrEnum, auto

from ccx_runner.ccx_logic.increment import Increment

class StepType(StrEnum):
    Static = auto()


class Step:
    def __init__(self, number: int, StepType: StepType) -> None:
        self.number = number
        self.type = StepType

        self.increments: list[Increment] = []

    @property
    def name(self) -> str:
        if self.type == StepType.Static:
            return f"StaticStep {self.number}"
        else:
            return f"Step {self.number}"
