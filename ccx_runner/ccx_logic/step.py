from enum import StrEnum, auto

class StepType(StrEnum):
    Static = auto()

class Step:
    def __init__(self, number:int, StepType:StepType) -> None:
        self.number = number
        self.type = StepType
        