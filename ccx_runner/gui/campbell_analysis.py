import dearpygui.dearpygui as dpg
import subprocess
import os
import shutil
import time
import threading
from pathlib import Path
import platformdirs
import json

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster

from ccx_runner.ccx_logic.run_ccx import run_ccx


class CampbellAnalysis:
    def __init__(self, hauptfenster: "Hauptfenster", tab_parent: int) -> None:
        self.hauptfenster = hauptfenster

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
            output_pfad = self.hauptfenster.job_dir / "campbell_analysis"
        else:
            output_pfad = Path(dpg.get_value(self.output_dir_input))

        if output_pfad.exists():
            # TODO safe version to clear data inside the directory
            if len(tuple(output_pfad.iterdir())) > 0:
                return
            # for item in output_pfad.iterdir():
            #     if item.is_file():
            #         item.unlink()
            #     elif item.is_dir():
            #         shutil.rmtree(item)
        else:
            # create output directory
            output_pfad.mkdir()

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

        project_files: list[tuple[str, float, Path]] = []
        # Setup a project directory for every speed step
        for i, speed in enumerate(speeds):
            name = f"simstep_{speed}_{i}"
            project_dir = output_pfad / name
            project_dir.mkdir()
            filepath = project_dir / (name + ".inp")

            # Modify speed value
            modified_project_file = original_inp.copy()
            parts = modified_project_file[line_number].split(",")
            parts[2] = str(speed)
            modified_project_file[line_number] = ",".join(parts)

            with open(filepath, "w") as inp_file:
                inp_file.writelines(modified_project_file)
            project_files.append((name, speed, project_dir))

        # run the analysis for every subproject
        for name, speed, project_dir in project_files:
            thread = threading.Thread(
                target=run_ccx,
                daemon=True,
                kwargs={
                    "ccx_path": self.hauptfenster.ccx_path,
                    "job_dir": project_dir,
                    "job_name": name,
                    "console_out": None,
                    "parser": None,
                    "finished": None,
                    "identifier":name
                },
            )
            thread.start()
