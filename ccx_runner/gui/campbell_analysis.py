import dearpygui.dearpygui as dpg
import subprocess
import os
import shutil
import time
import threading
from pathlib import Path
import platformdirs
import json

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster


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
        self.speeds_input = dpg.add_input_text(label="List of speeds [rad/time]", hint="50,150,300,500.5")
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
        dpg.configure_item(self.output_dir_input, hint=self.hauptfenster.job_dir / "campbell_analysis")

    def run_campbell_analysis(self):
        if dpg.get_value(self.output_dir_input) == "":
            output_pfad = self.hauptfenster.job_dir / "campbell_analysis"
        else:
            output_pfad = Path(dpg.get_value(self.output_dir_input))
        
        if output_pfad.exists():
            # TODO safe version to clear data inside the directory
            if len(tuple(output_pfad.iterdir()))>0:
                return
            # for item in output_pfad.iterdir():
            #     if item.is_file():
            #         item.unlink()
            #     elif item.is_dir():
            #         shutil.rmtree(item)
        else:
            # create output directory
            output_pfad.mkdir()
        
        
        