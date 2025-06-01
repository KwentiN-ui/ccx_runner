import dearpygui.dearpygui as dpg
import subprocess
import os
import threading
from pathlib import Path
import platformdirs
import json

from ccx_runner.ccx_logic.ccx_status import CalculixStatus


class Hauptfenster:
    def __init__(self) -> None:

        self._console_out: list[str] = []
        self.status = CalculixStatus(self)

        # SETUP GUI
        with dpg.window(label="Example Window") as self.id:
            self.ccx_name_inp = dpg.add_input_text(label="Solver Pfad")
            self.job_directory_inp = dpg.add_input_text(label="Job Directory")
            with dpg.group(horizontal=True):
                self.job_name_inp = dpg.add_combo()
                dpg.add_button(label="refresh", callback=self.update_available_jobs)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Run Job", callback=self.start_job)
                self.kill_job_btn = dpg.add_button(
                    label="Stop Job", callback=self.kill_job, show=False
                )

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
                    self.step_selection_combo = dpg.add_combo(
                        label="Step", callback=self.update_solver_status
                    )

                    # Übersichtstabelle
                    with dpg.table() as self.table:
                        dpg.add_table_column(label="Increment #")
                        dpg.add_table_column(label="Attempt")
                        dpg.add_table_column(label="Iterations")
                        dpg.add_table_column(label="delta Time")
                        dpg.add_table_column(label="total Time")

                with dpg.tab(label="Residuals"):
                    self.plotted_keys = []
                    with dpg.plot(width=-1, height=-1) as self.plot:
                        dpg.add_plot_legend()

                        self.plot_x_axis = dpg.add_plot_axis(
                            dpg.mvXAxis, label="Iteration", auto_fit=True
                        )
                        self.plot_y_axis = dpg.add_plot_axis(
                            dpg.mvYAxis, label="Residual", auto_fit=True
                        )

        self.path_manager = ConfigManager("ccx_runner")
        last_known_paths = self.path_manager.load_paths()
        dpg.configure_item(
            self.ccx_name_inp, default_value=last_known_paths.get("ccx_name", "")
        )
        dpg.configure_item(
            self.job_directory_inp, default_value=last_known_paths.get("job_dir", "")
        )

        self.update_available_jobs()
        self.process = None

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
    def job_name(self):
        return dpg.get_value(self.job_name_inp)

    def update_solver_status(self):
        dpg.configure_item(
            self.step_selection_combo, items=[step.name for step in self.status.steps]
        )
        # Clear all rows from the table
        for child in dpg.get_item_children(self.table, slot=1):  # type: ignore
            dpg.delete_item(child)
        step = self.selected_step
        if step:
            for increment in step.increments:
                with dpg.table_row(parent=self.table):
                    dpg.add_text(str(increment.number))  # Increment #
                    dpg.add_text(str(increment.attempt))  # Attempt
                    dpg.add_text(str(len(increment.iterations)))  # Increments
                    dpg.add_text(str(increment.incremental_time))  # delta T
                    dpg.add_text(str(increment.total_time))  # total T

        if self.status.steps:
            step = self.status.steps[-1]
            if step.increments:
                for label, data in step.increments[-1].residuals.items():
                    if label not in self.plotted_keys:
                        self.plotted_keys.append(label)
                        dpg.add_line_series(
                            tuple(range(len(data))),
                            data,
                            label=label,
                            parent=self.plot_y_axis,
                            tag=label,
                        )
                    else:
                        dpg.set_value(label, [tuple(range(len(data))), data])

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

    def add_console_text(self, text: str):
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

    def run_ccx(self):
        """
        Runs the calculix subprocess and monitors its outputs.
        """
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
        self.status.running = True
        self.process = subprocess.Popen(
            [f"{self.ccx_path.resolve()}", f"{self.job_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.job_dir.resolve(),
        )

        while self.process.poll() is None:
            if self.process.stdout:
                for line in self.process.stdout:
                    self.add_console_text(line)
                    self.status.parse(line)

            if self.process.stderr:
                for line in self.process.stderr:
                    self.add_console_text(line)

        return_code = self.process.returncode
        if return_code != 0:
            self.add_console_text(f"ccx exited with error code: {return_code}")

        self.reset_after_process()

    def reset_after_process(self):
        dpg.hide_item(self.kill_job_btn)
        self.process = None
        self.status.running = False

    def start_job(self):
        if self.process is not None:  # Prevent starting multiple jobs
            return

        dpg.show_item(self.kill_job_btn)
        dpg.set_value(self.console_out, "")
        self._console_out.clear()

        self.thread = threading.Thread(target=self.run_ccx, daemon=True)
        self.thread.start()

    def kill_job(self):
        if self.process:
            self.process.kill()


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
