import numpy as np
import itertools
from functools import cached_property


class ResultBlock:
    def __init__(self, frd: list[str], beginn: int) -> None:
        self.frd = frd
        self.beginn = beginn
        self.header: dict[str, list[str]] = {}  # header: args
        self.output_type = ""
        self.components: list[str] = []

        curline = beginn
        # Parse Header section
        while not frd[curline].strip().startswith("-4"):
            line = frd[curline]
            contents = line.split()
            self.header[contents[0]] = contents[1:]
            curline += 1

        # Parse Components
        while not frd[curline].strip().startswith("-1"):
            line = frd[curline].strip()
            if line.startswith("-4"):
                self.output_type = line.split()[1]
            if line.startswith("-5"):
                self.components.append(line.split()[1])
            curline += 1

        self.data_begin = curline

    def __repr__(self) -> str:
        return "|".join(tuple(self.header.keys()))

    @cached_property
    def data(self):
        """
        Extracts all the data as one large Numpy Array.
        """
        frd = self.frd
        curline = self.data_begin
        all_lines = []
        while frd[curline].strip().startswith("-1"):
            line = frd[curline].strip()
            components_str = line.removeprefix("-1")
            node = int(components_str[:10])
            fields = [
                float("".join(batch))
                for batch in itertools.batched(components_str[10:], 12)
            ]
            all_lines.append([node] + fields)

            curline += 1
        return np.array(all_lines)

    @staticmethod
    def from_frd(frd: str) -> list["ResultBlock"]:
        results: list[ResultBlock] = []
        lines = frd.splitlines()
        for nr, line in enumerate(lines):
            if "1PSTEP" in line:
                # new results block begins
                results.append(ResultBlock(lines, nr))

        return results


# TESTCODE
if __name__ == "__main__":
    with open("/home/qhuss/Downloads/simstep_0.0_0.frd", "r") as file1:
        frd_1 = file1.read()

    with open("/home/qhuss/Downloads/simstep_785.3985_1.frd", "r") as file2:
        frd_2 = file2.read()

