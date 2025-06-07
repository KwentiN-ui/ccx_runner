import numpy as np
import itertools
import textwrap
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


class Eigenvector:
    def __init__(self, result: ResultBlock) -> None:
        self.result = result

    def __repr__(self) -> str:
        return f"({self.step}) Mode {self.mode_nr} [{self.eigenfrequency} Hz]"

    @property
    def step(self):
        return int(self.result.header["100CL"][3])

    @property
    def eigenfrequency(self):
        return float(self.result.header["100CL"][1])

    @property
    def mode_nr(self):
        return int(self.result.header["1PMODE"][0])

    @property
    def data(self):
        return self.result.data

    @staticmethod
    def from_result_blocks(results: list[ResultBlock]):
        eigenvectors: list["Eigenvector"] = []
        for res in results:
            if res.output_type == "DISP" and "1PMODE" in tuple(res.header.keys()):
                eigenvectors.append(Eigenvector(res))
        return eigenvectors

    def mac(self, other: "Eigenvector") -> float:
        r"""
        Compute the Modal Assurance Criterion. This assigns a scalar value between 0 and 1 which
        describes the similarity between the two node shapes. This is needed to correctly identify
        the same node shapes between different simulations.

        $$
        \text{MAC}(\{\phi_A\}, \{\phi_B\}) = \frac{|(\{\phi_A\}^T \{\phi_B\})|^2}{(\{\phi_A\}^T \{\phi_A\}) (\{\phi_B\}^T \{\phi_B\})}
        $$
        """
        mode_1_data = self.data
        mode_2_data = other.data

        sort_indices = mode_1_data[:, 0].argsort()

        sorted_1 = mode_1_data[sort_indices]
        sorted_2 = mode_2_data[sort_indices]

        # Sicherheitscheck (optional, aber empfohlen)
        # Stellt sicher, dass die Knoten-IDs jetzt wirklich übereinstimmen
        assert np.array_equal(
            sorted_1[:, 0], sorted_2[:, 0]
        ), "Knoten-IDs stimmen nach Sortierung nicht überein!"

        flattened_1 = sorted_1[:, 1:].flatten()
        flattened_2 = sorted_2[:, 1:].flatten()

        numerator = np.abs(np.dot(flattened_1, flattened_2)) ** 2
        denominator = np.dot(flattened_1, flattened_1) * np.dot(
            flattened_2, flattened_2
        )

        mac_value = 0.0
        if denominator > 1e-12:  # Avoid Zero Division
            mac_value = numerator / denominator
        return mac_value


def calculate_mac_matrix(frd_1: str, frd_2: str, step: int = 3):
    "Computes the MAC in order to find matching Modes between 2 different Modal Simulation Results"
    res1 = ResultBlock.from_frd(frd_1)
    res2 = ResultBlock.from_frd(frd_2)

    eigenvects1 = [
        vec for vec in Eigenvector.from_result_blocks(res1) if vec.step == step
    ]
    eigenvects2 = [
        vec for vec in Eigenvector.from_result_blocks(res2) if vec.step == step
    ]
    # print(eigenvects1[0].data.shape)
    print(mac(eigenvects1[3], eigenvects2[2]))


if __name__ == "__main__":
    with open("/home/qhuss/Downloads/simstep_0.0_0.frd", "r") as file1:
        frd_1 = file1.read()

    with open("/home/qhuss/Downloads/simstep_785.3985_1.frd", "r") as file2:
        frd_2 = file2.read()

    calculate_mac_matrix(frd_1, frd_2)
