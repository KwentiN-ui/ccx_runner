import dearpygui.dearpygui as dpg
import subprocess
import os
import time
import threading
from pathlib import Path
import platformdirs
import json
from typing import Optional

from ccx_runner.ccx_logic.status import CalculixStatus
from ccx_runner.gui.campbell_analysis import CampbellAnalysis
from ccx_runner.ccx_logic.run_ccx import run_ccx

class Hauptfenster:
    def __init__(self) -> None:
        self.startzeit = 0
        self._console_out: list[str] = []
        self.status = CalculixStatus(self)
        dpg.set_exit_callback(self.kill_job)
        # SETUP GUI
        with dpg.window(label="Example Window") as self.id:
            self.ccx_name_inp = dpg.add_input_text(label="Solver Pfad")
            self.job_directory_inp = dpg.add_input_text(
                label="Job Directory",
                callback=self.callback_project_directory_changed,
                tracked=True,
            )
            with dpg.group(horizontal=True):
                self.job_name_inp = dpg.add_combo(
                    callback=self.callback_project_selected
                )
                dpg.add_button(label="refresh", callback=self.update_available_jobs)

            with dpg.group(horizontal=True):
                self.start_job_btn = dpg.add_button(
                    label="Run Job", callback=self.start_job
                )
                self.kill_job_btn = dpg.add_button(
                    label="Stop Job", callback=self.kill_job, show=False
                )
                self.timer = dpg.add_text(show=False)

            with dpg.tab_bar() as self.tab_bar:
                with dpg.tab(label="Console"):
                    self.console_filter_input = dpg.add_input_text(
                        callback=self.update_console_output,
                        hint='Filter for keywords, use "|" for multiple',
                    )
                    self.console_out = dpg.add_input_text(
                        multiline=True, readonly=True, height=-1
                    )

                with dpg.tab(label="Overview"):
                    # Residual Plot
                    self._plotted_keys = []
                    with dpg.plot(width=-1) as self.plot:
                        dpg.add_plot_legend()

                        self.plot_x_axis = dpg.add_plot_axis(
                            dpg.mvXAxis, label="Iteration", auto_fit=True
                        )
                        self.plot_y_axis = dpg.add_plot_axis(
                            dpg.mvYAxis, label="Residual", auto_fit=True
                        )

                    # Table
                    self.step_selection_combo = dpg.add_combo(
                        label="Step", callback=self.update_solver_status
                    )
                    self.table = dpg.add_table(height=-1)

                with dpg.tab(label="Complex Frequency Analysis") as tab_id:
                    self.cambell_analysis = CampbellAnalysis(self, tab_id)

        self.path_manager = ConfigManager("ccx_runner")
        last_known_paths = self.path_manager.load_paths()
        dpg.set_value(self.ccx_name_inp, last_known_paths.get("ccx_name", ""))
        dpg.set_value(self.job_directory_inp, last_known_paths.get("job_dir", ""))
        self.callback_project_directory_changed()

        self.update_available_jobs()
        self.process = None

    def callback_project_selected(self):
        self.cambell_analysis.callback_project_selected()

    def callback_project_directory_changed(self):
        self.cambell_analysis.callback_project_directory_changed()

    def update_table_data(self):
        step = self.selected_step
        if not step:
            return

        # reset Table
        dpg.delete_item(self.table, children_only=True)

        data = step.tabular_data
        for header in data.keys():
            dpg.add_table_column(label=header, parent=self.table)
        for zeile in zip(*data.values()):
            with dpg.table_row(parent=self.table):
                for eintrag in zeile:
                    dpg.add_text(str(eintrag))

    def update_residual_plot(self):
        if self.status.steps:
            step = self.status.steps[-1]
            for label, data in step.residuals.items():
                if label not in self._plotted_keys:
                    self._plotted_keys.append(label)
                    dpg.add_line_series(
                        tuple(range(len(data))),
                        data,
                        label=label,
                        parent=self.plot_y_axis,
                        tag=label,
                    )
                else:
                    dpg.set_value(label, [tuple(range(len(data))), data])

    @property
    def selected_step(self):
        selection = dpg.get_value(self.step_selection_combo)
        for step in self.status.steps:
            if step.name == selection:
                return step

    @property
    def ccx_path(self):
        return Path(dpg.get_value(self.ccx_name_inp))

    @property
    def job_dir(self):
        return Path(dpg.get_value(self.job_directory_inp))

    @property
    def job_name(self) -> str:
        """
        Job name without a file ending.
        """
        return dpg.get_value(self.job_name_inp)

    def update_solver_status(self):
        """
        Redraw the Overview table and residual plot.
        """
        dpg.configure_item(
            self.step_selection_combo, items=[step.name for step in self.status.steps]
        )
        self.update_table_data()
        self.update_residual_plot()

    def update_console_output(self):
        query: str = dpg.get_value(self.console_filter_input)
        if query == "":
            dpg.set_value(self.console_out, "".join(self._console_out))
        else:
            suchbegriffe = [wort.strip() for wort in query.split("|")]
            dpg.set_value(
                self.console_out,
                "".join(
                    [
                        line
                        for line in self._console_out
                        if any(suchbegriff in line for suchbegriff in suchbegriffe)
                    ]
                ),
            )

    def reset_residual_plot(self):
        self._plotted_keys = []
        dpg.delete_item(self.plot_y_axis, children_only=True)

    def add_console_text(self, text: str, *args):
        self._console_out.append(text)
        self.update_console_output()

    def update_available_jobs(self):
        try:
            items: list[str] = [
                datei.split(".")[0]
                for datei in os.listdir(dpg.get_value(self.job_directory_inp))
                if datei.endswith(".inp")
            ]
        except FileNotFoundError:
            items = []

        dpg.configure_item(
            self.job_name_inp,
            items=items,
        )

    def reset_after_process(self, identifier:Optional[str]=None):
        dpg.hide_item(self.kill_job_btn)
        dpg.show_item(self.start_job_btn)
        self.process = None
        self.status.running = False

    def start_job(self):
        if self.process is not None:  # Prevent starting multiple jobs
            return

        self.reset_residual_plot()
        dpg.show_item(self.kill_job_btn)
        dpg.hide_item(self.start_job_btn)
        dpg.set_value(self.console_out, "")
        self._console_out.clear()

        # Check if paths are valid
        if not self.ccx_path.is_file():
            self.add_console_text(
                f'The given filepath for the Calculix Binary does not point to a file!:\n"{self.ccx_path}"'
            )
            return
        if not self.job_dir.is_dir():
            self.add_console_text(
                f'The given path for the job directory does not point to a directory!:\n"{self.job_dir}"'
            )
            return

        self.path_manager.save_paths(
            {
                "ccx_name": dpg.get_value(self.ccx_name_inp),
                "job_dir": dpg.get_value(self.job_directory_inp),
            }
        )

        self.status = CalculixStatus(self)
        self.startzeit = time.time()
        dpg.show_item(self.timer)
        self.status.running = True

        self.thread = threading.Thread(target=run_ccx, daemon=True, kwargs= {
            "ccx_path": self.ccx_path,
            "job_dir": self.job_dir,
            "job_name": self.job_name,
            "console_out": self.add_console_text,
            "parser": self.status.parse,
            "finished": self.reset_after_process,
            "identifier": "main thread"
        })
        self.thread.start()

    def kill_job(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.reset_after_process()
            self.add_console_text("Process successfully aborted!")

    def update(self):
        """
        This runs for every frame
        """
        if self.status.running:
            dpg.set_value(self.timer, f"{round(time.time() - self.startzeit,2)}s")


class ConfigManager:
    """Handles the saving and loading of user configuration data as a JSON in the users config directory."""

    def __init__(self, app_name: str):
        # Gets the path to the users config directory (works for every platform)
        self.config_dir = Path(platformdirs.user_config_dir("ccx_runner"))
        self.config_file = self.config_dir / "config.json"

        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_paths(self, paths: dict):
        """Saves configuration data as a JSON-file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(paths, f, indent=4)
            # print(f"Pfade gespeichert in: {self.config_file}")
        except IOError as e:
            print(f"Fehler beim Speichern der Pfade: {e}")

    def load_paths(self) -> dict:
        """Loads config data from the json data file. Returns empty if it doesnt exist."""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, "r") as f:
                paths = json.load(f)
                return paths
        except (IOError, json.JSONDecodeError) as e:
            return {}
