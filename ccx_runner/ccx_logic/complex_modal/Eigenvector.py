from ccx_runner.ccx_logic.result import ResultBlock

import numpy as np


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
