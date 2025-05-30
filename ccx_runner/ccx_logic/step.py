from enum import StrEnum, auto


class StepType(StrEnum):
    Static = auto()


class Step:
    def __init__(self, number: int, StepType: StepType) -> None:
        self.number = number
        self.type = StepType

    @property
    def name(self) -> str:
        if self.type == StepType.Static:
            return f"StaticStep {self.number}"
        else:
            return f"Step {self.number}"
