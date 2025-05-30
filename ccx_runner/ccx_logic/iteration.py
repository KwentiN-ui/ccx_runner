from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.ccx_logic.increment import Increment


class Iteration:
    def __init__(self, increment: "Increment", number: int) -> None:
        self.increment = increment
        self.number = number
        self.data: dict[str, float] = {}
