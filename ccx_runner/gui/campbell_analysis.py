import dearpygui.dearpygui as dpg
import threading
from pathlib import Path
import numpy as np
import collections
import tempfile

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster

from ccx_runner.ccx_logic.run_ccx import run_ccx


class CampbellAnalysis:
    def __init__(self, hauptfenster: "Hauptfenster", tab_parent: int) -> None:
        self.hauptfenster = hauptfenster
        self.project_instance_data = {}
        self.plot_window = CampbellPlot(self)

        self.results: dict[float, dict[int, tuple[float, float]]] = {}

        dpg.add_text(
            'This tab provides the tools to parametrize a "*COMPLEX FREQUENCY, CORIOLIS" step,'
            " by running the analysis multiple times with different speeds. The complex frequency step gets automatically inserted if missing, but a standard frequency step is mandatory.",
            wrap=500,
            parent=tab_parent,
        )
        self.centrif_load_name = dpg.add_combo(
            label="Centrifugal load", parent=tab_parent
        )
        self.speeds_input = dpg.add_input_text(
            label="List of speeds [rad/time]", hint="50,150,300,500.5"
        )

        with dpg.group(horizontal=True, parent=tab_parent):
            dpg.add_button(label="Run Analysis", callback=self.run_campbell_analysis)
            self.plot_button = dpg.add_button(
                label="Show Plot", show=False, callback=self.plot_window.show
            )
            self.number_of_threads_input = dpg.add_input_int(
                default_value=3,
                label="Number of threads",
                width=100,
                min_value=1,
                min_clamped=True,
            )

        self.tab_bar = dpg.add_tab_bar(parent=tab_parent)

    def callback_project_selected(self):
        # get all available centrif definitions from the .inp file
        centrif_definitions: list[str] = []

        project_file = self.hauptfenster.project_file_contents
        if not project_file:
            return
        for line in project_file.splitlines():
            if "centrif" in line.lower() and len(line.split(",")) == 9:
                name = line.split(",")[0].strip()
                centrif_definitions.append(name)
        dpg.configure_item(self.centrif_load_name, items=centrif_definitions)
        if len(centrif_definitions) > 0:
            dpg.set_value(self.centrif_load_name, centrif_definitions[0])

    @property
    def project_contains_complex_freq_step(self):
        """
        Checks the `.inp` file for a `*COMPLEX FREQUENCY, CORIOLIS` step.
        """
        input_file = self.hauptfenster.project_file_contents
        if input_file is None:
            raise ValueError("The input file could not be read.")
        searchwords = ["*complex frequency", "coriolis"]
        for line in input_file.splitlines():
            if all(searchword in line.lower() for searchword in searchwords):
                return True
        else:
            return False

    @property
    def project_with_added_complex_freq_step(self) -> str:
        project_file = self.hauptfenster.project_file_contents
        if project_file is None:
            raise ValueError("Project file could not be read!")
        if self.project_contains_complex_freq_step:
            return project_file
        else:
            # get the frequency step substring
            start_index: Optional[int] = None
            end_index: Optional[int] = None
            lines = [line.strip() for line in project_file.splitlines()]
            for nr, line in enumerate(lines):
                if line.lower().startswith("*step") and lines[
                    nr + 1
                ].lower().startswith("*frequency"):
                    start_index = nr

                if start_index is not None and line.lower().startswith("*end step"):
                    end_index = nr
                    break
            if start_index is None or end_index is None:
                raise ValueError("No Frequency Step found in the .inp file")
            freq_step_lines = [
                line.lower()
                for line in lines[start_index : end_index + 1]
                if not line.strip().startswith("**")
            ]
            freq_step_lines[1] = freq_step_lines[1].replace(
                "frequency", "complex frequency,coriolis"
            )
            return project_file + "\n" + "\n".join(freq_step_lines)

    @property
    def speeds(self):
        speeds_inp: str = dpg.get_value(self.speeds_input)
        if speeds_inp:
            return [float(speed) for speed in speeds_inp.split(",")]

    @property
    def modal_data(self) -> dict[int, dict[str, list[float]]]:
        mod_data = collections.defaultdict(
            lambda: {"speed": [], "freq": [], "real": [], "imag": []}
        )

        for speed, modes in self.results.items():
            for mode_nr, (real, imag) in modes.items():
                mod_data[mode_nr]["speed"].append(speed / (2 * np.pi))
                mod_data[mode_nr]["freq"].append(abs(real / (2 * np.pi)))
                mod_data[mode_nr]["real"].append(real)
                mod_data[mode_nr]["imag"].append(imag)

        # 3. Sortierschritt anpassen, um alle vier Listen zu synchronisieren
        for mode_nr in mod_data:
            # Alle vier Listen koppeln
            paired_data = zip(
                mod_data[mode_nr]["speed"],
                mod_data[mode_nr]["freq"],
                mod_data[mode_nr]["real"],
                mod_data[mode_nr]["imag"],
            )

            # Nach Geschwindigkeit sortieren
            sorted_pairs = sorted(paired_data)

            # Gekoppelte Daten wieder in die vier Listen trennen
            if sorted_pairs:
                s_sort, m_sort, r_sort, i_sort = zip(*sorted_pairs)
            else:
                s_sort, m_sort, r_sort, i_sort = [], [], [], []

            # Dictionary mit den sortierten Listen aktualisieren
            mod_data[mode_nr]["speed"] = list(s_sort)
            mod_data[mode_nr]["freq"] = list(m_sort)
            mod_data[mode_nr]["real"] = list(r_sort)
            mod_data[mode_nr]["imag"] = list(i_sort)

        return mod_data

    def run_cxx_limited_concurrency(self, **kwargs):
        with self.thread_pool:
            run_ccx(**kwargs)

    def run_campbell_analysis(self):
        ### CHECKS BEFORE STARTING
        boundary_name = dpg.get_value(self.centrif_load_name)
        if boundary_name == "":
            return
        speeds = self.speeds
        if speeds is None:
            return
        dpg.hide_item(self.plot_button)
        ### HANDLE OUTPUT DIRECTORY ###
        n_threads = dpg.get_value(self.number_of_threads_input)
        self.thread_pool = threading.Semaphore(n_threads)
        self.tempdir = tempfile.TemporaryDirectory(
            "ccx_complex_freq_analysis", delete=False
        )
        temp_pfad = Path(self.tempdir.name)

        inp_file = self.project_with_added_complex_freq_step.splitlines()

        line_number: Optional[int] = None
        for nr, line in enumerate(inp_file):
            if (
                boundary_name in line
                and "centrif" in line.lower()
                and len(line.split(",")) == 9
            ):
                line_number = nr
        assert (
            line_number is not None
        ), "For some reason, the specified centrif value was not found inside the .inp file."

        self.project_files: list[tuple[str, float, Path]] = []
        # Setup a project directory for every speed step
        for i, speed in enumerate(speeds):
            name = f"simstep_{speed}_{i}"
            project_dir = temp_pfad / name
            project_dir.mkdir()
            filepath = project_dir / (name + ".inp")

            # Modify speed value
            modified_project_file = inp_file.copy()
            parts = modified_project_file[line_number].split(",")
            parts[2] = str(speed)
            modified_project_file[line_number] = ",".join(parts)

            with open(filepath, "w") as file:
                file.write("\n".join(modified_project_file))
            self.project_files.append((name, speed, project_dir))

        # run the analysis for every subproject
        dpg.delete_item(self.tab_bar, children_only=True)
        self.project_instance_data = {}
        for name, speed, project_dir in self.project_files:
            self.project_instance_data[name] = {}
            with dpg.tab(label=str(speed), parent=self.tab_bar):
                self.project_instance_data[name]["textbox"] = dpg.add_input_text(
                    readonly=True, multiline=True, width=-1, height=-1
                )
                self.project_instance_data[name]["running"] = False
                self.project_instance_data[name]["finished"] = False

            thread = threading.Thread(
                target=self.run_cxx_limited_concurrency,
                daemon=True,
                kwargs={
                    "ccx_path": self.hauptfenster.ccx_path,
                    "job_dir": project_dir,
                    "job_name": name,
                    "console_out": self.console_out,
                    "parser": None,
                    "finished": self.mark_as_finished,
                    "identifier": name,
                },
            )
            thread.start()

    def console_out(self, line: str, identifier: Optional[str]):
        textbox = self.project_instance_data[identifier]["textbox"]
        dpg.set_value(textbox, dpg.get_value(textbox) + line)

    def mark_as_finished(self, identifier: Optional[str]):
        self.project_instance_data[identifier]["finished"] = True
        if all(
            self.project_instance_data[ident]["finished"]
            for ident in self.project_instance_data.keys()
        ):
            self.all_thread_complete()

    def all_thread_complete(self):
        self.results = {}
        # Collect all the Modal Analysis result files
        for name, speed, project_dir in self.project_files:
            with open(project_dir / (name + ".dat"), "r") as result_file:
                result_file_contents = result_file.read()
            parser = ComplexModalParseResult(result_file_contents, speed)
            self.results[speed] = parser.eigenvalue_output
        dpg.show_item(self.plot_button)
        self.tempdir.cleanup()


class CampbellPlot:
    def __init__(self, analysis: CampbellAnalysis) -> None:
        self.analysis = analysis
        with dpg.window(show=False) as self.window_id:
            with dpg.plot(width=-1, height=-1):
                dpg.add_plot_axis(dpg.mvXAxis, label="revolution speed [Hz]")
                self.plot_axis = dpg.add_plot_axis(
                    dpg.mvYAxis, label="Eigenfrequency [Hz]"
                )

    def show(self):
        dpg.show_item(self.window_id)
        dpg.delete_item(self.plot_axis, children_only=True)
        for mode, daten in enumerate(self.analysis.modal_data.values()):
            speed, real, imag, freq = (
                np.array(daten["speed"]),
                np.array(daten["real"]),
                np.array(daten["imag"]),
                np.array(daten["freq"]),
            )
            dpg.add_line_series(tuple(speed), tuple(freq), parent=self.plot_axis)
        if self.analysis.speeds:
            max_speed = max(self.analysis.speeds) / (2 * np.pi)
            for i in range(3):
                dpg.add_line_series(
                    [0, max_speed], [0, (i + 1) * max_speed], parent=self.plot_axis
                )


class ComplexModalParseResult:
    def __init__(self, file_contents: str, speed: float) -> None:
        self.speed = speed
        self.file_contents = file_contents
        self._eigenvalue_output: dict[int, tuple[float, float]] = {}
        self._modal_assurance_matrix: np.ndarray
        self.parse()

    @property
    def eigenvalue_output(self) -> dict[int, tuple[float, float]]:
        """
        Dictionary that stores the Modal Data for a specific speed as `{modenr:(real[rad/time],complex[rad/time])}`
        """
        return self._eigenvalue_output

    def parse(self):
        lines = self.file_contents.splitlines()
        counter = 0
        startzeile: Optional[int] = None
        for nr, line in enumerate(lines):
            if "E I G E N V A L U E   O U T P U T" in line:
                counter += 1
                if counter == 2:
                    startzeile = nr + 6

        if startzeile is None:
            raise ValueError("Es wurde kein COMPLEX FREQUENCY output gefunden!")
        else:
            curline = startzeile
            while len(lines[curline].strip()) > 0:
                mode_no, real_rad, real_cycl, imag_rad = (
                    data.strip() for data in lines[curline].strip().split("  ")
                )
                real = float(real_rad)
                imag = float(imag_rad)
                self._eigenvalue_output[int(mode_no)] = (real, imag)
                curline += 1
