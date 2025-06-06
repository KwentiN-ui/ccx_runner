import dearpygui.dearpygui as dpg
import threading
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import collections

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster

from ccx_runner.ccx_logic.run_ccx import run_ccx


class CampbellAnalysis:
    def __init__(self, hauptfenster: "Hauptfenster", tab_parent: int) -> None:
        self.hauptfenster = hauptfenster
        self.project_instance_data = {}

        self.results: dict[float, dict[int, tuple[float, float]]] = {}

        dpg.add_text(
            'This tab provides the tools to parametrize a "*COMPLEX FREQUENCY, CORIOLIS" step,'
            " by running the analysis multiple times with different speeds.",
            wrap=500,
            parent=tab_parent,
        )
        self.centrif_load_name = dpg.add_combo(
            label="Centrifugal load", parent=tab_parent
        )
        self.speeds_input = dpg.add_input_text(
            label="List of speeds [rad/time]", hint="50,150,300,500.5"
        )
        self.output_dir_input = dpg.add_input_text(label="output directory")

        with dpg.group(horizontal=True, parent=tab_parent):
            dpg.add_button(label="Run Analysis", callback=self.run_campbell_analysis)

        self.tab_bar = dpg.add_tab_bar(parent=tab_parent)

    def callback_project_selected(self):
        # get all available centrif definitions from the .inp file
        centrif_definitions: list[str] = []
        with open(
            self.hauptfenster.job_dir / (self.hauptfenster.job_name + ".inp"), "r"
        ) as inp_file:
            for line in inp_file.readlines():
                if "centrif" in line.lower() and len(line.split(",")) == 9:
                    name = line.split(",")[0].strip()
                    centrif_definitions.append(name)
        dpg.configure_item(self.centrif_load_name, items=centrif_definitions)
        if len(centrif_definitions) > 0:
            dpg.set_value(self.centrif_load_name, centrif_definitions[0])

    def callback_project_directory_changed(self):
        dpg.configure_item(
            self.output_dir_input, hint=self.hauptfenster.job_dir / "campbell_analysis"
        )

    @property
    def speeds(self):
        speeds_inp: str = dpg.get_value(self.speeds_input)
        if speeds_inp:
            return [float(speed) for speed in speeds_inp.split(",")]

    @property
    def modal_data(self) -> dict[int, dict[str, list[float]]]:
        mod_data = collections.defaultdict(
            lambda: {"speed": [], "magnitude": [], "real": [], "imag": []}
        )

        for speed, modes in self.results.items():
            for mode_nr, (real, imag) in modes.items():
                mod_data[mode_nr]["speed"].append(speed)
                mod_data[mode_nr]["magnitude"].append(abs(real + 1j * imag))
                mod_data[mode_nr]["real"].append(real)
                mod_data[mode_nr]["imag"].append(imag)

        # 3. Sortierschritt anpassen, um alle vier Listen zu synchronisieren
        for mode_nr in mod_data:
            # Alle vier Listen koppeln
            paired_data = zip(
                mod_data[mode_nr]["speed"],
                mod_data[mode_nr]["magnitude"],
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
            mod_data[mode_nr]["magnitude"] = list(m_sort)
            mod_data[mode_nr]["real"] = list(r_sort)
            mod_data[mode_nr]["imag"] = list(i_sort)

        return mod_data

    def run_campbell_analysis(self):
        ### CHECKS BEFORE STARTING
        boundary_name = dpg.get_value(self.centrif_load_name)
        if boundary_name == "":
            return
        speeds = self.speeds
        if speeds is None:
            return

        ### HANDLE OUTPUT DIRECTORY ###
        if dpg.get_value(self.output_dir_input) == "":
            self.output_pfad = self.hauptfenster.job_dir / "campbell_analysis"
        else:
            self.output_pfad = Path(dpg.get_value(self.output_dir_input))

        if self.output_pfad.exists():
            # TODO change to a tmp dir
            if len(tuple(self.output_pfad.iterdir())) > 0:
                return
            # for item in output_pfad.iterdir():
            #     if item.is_file():
            #         item.unlink()
            #     elif item.is_dir():
            #         shutil.rmtree(item)
        else:
            # create output directory
            self.output_pfad.mkdir()

        ### READ JOB DATA FROM .inp FILE
        with open(
            self.hauptfenster.job_dir / (self.hauptfenster.job_name + ".inp"), "r"
        ) as inp_file:
            original_inp = inp_file.readlines()

        line_number: Optional[int] = None
        for nr, line in enumerate(original_inp):
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
            project_dir = self.output_pfad / name
            project_dir.mkdir()
            filepath = project_dir / (name + ".inp")

            # Modify speed value
            modified_project_file = original_inp.copy()
            parts = modified_project_file[line_number].split(",")
            parts[2] = str(speed)
            modified_project_file[line_number] = ",".join(parts)

            with open(filepath, "w") as inp_file:
                inp_file.writelines(modified_project_file)
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
                self.project_instance_data[name]["finished"] = False

            thread = threading.Thread(
                target=run_ccx,
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
            parser = ComplexModalParser(result_file_contents)
            self.results[speed] = parser.data

        print(self.results)


class ComplexModalParser:
    def __init__(self, file_contents: str) -> None:
        self.file_contents = file_contents
        self._data: dict[int, tuple[float, float]] = {}
        self.parse()

    @property
    def data(self) -> dict[int, tuple[float, float]]:
        """
        Dictionary that stores the Modal Data for a specific speed as `{modenr:(real[rad/time],complex[rad/time])}`
        """
        return self._data

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
                if abs(real) > 1e-5: # filter freq too close to zero
                    self._data[int(mode_no)] = (real, imag)
                curline += 1
