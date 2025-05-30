import dearpygui.dearpygui as dpg
import subprocess
import sys
import os
import threading
import time

from ccx_runner.ccx_logic.ccx_status import CalculixStatus


class Hauptfenster:
    def __init__(self) -> None:
        self._console_out: list[str] = []
        self.status = CalculixStatus(self)

        with dpg.window(label="Example Window") as self.id:
            self.ccx_name_inp = dpg.add_input_text(
                label="Solver Name", default_value="ccx_2.19_MT"
            )
            self.job_directory_inp = dpg.add_input_text(
                label="Job Directory",
                default_value="/media/qhuss/76a9dfaf-c78f-4c2f-a48c-5a6b936cdb8d/PrePoMax/PrePoMax v2.3.4 dev/Temp/",
            )
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
                        label="search", callback=self.callback_filter_input
                    )
                    with dpg.child_window(height=-1) as self.console_out_cw:
                        self.console_out = dpg.add_input_text(
                            multiline=True, readonly=True, height=-1
                        )
                with dpg.tab(label="Overview"):
                    self.step_selection_combo = dpg.add_combo(
                        callback=self.update_solver_status
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

        self.update_available_jobs()
        self.process = None

    @property
    def selected_step(self):
        selection = dpg.get_value(self.step_selection_combo)
        for step in self.status.steps:
            if step.name == selection:
                return step

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
            if self.status.steps[-1].increments:
                for label, data in (
                    self.status.steps[-1].increments[-1].residuals.items()
                ):
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

    def callback_filter_input(self):
        query = dpg.get_value(self.console_filter_input)
        if query == "":
            dpg.set_value(self.console_out, "".join(self._console_out))
        else:
            dpg.set_value(
                self.console_out,
                "".join([line for line in self._console_out if query in line]),
            )

    def add_console_text(self, text: str):
        self._console_out.append(text)
        dpg.set_value(self.console_out, "".join(self._console_out))

    def update_available_jobs(self):
        dpg.configure_item(
            self.job_name_inp,
            items=[
                datei.split(".")[0]
                for datei in os.listdir(dpg.get_value(self.job_directory_inp))
                if datei.endswith(".inp")
            ],
        )

    def run_ccx(self):
        self.status = CalculixStatus(self)
        self.status.running = True
        projekt = os.path.join(
            dpg.get_value(self.job_directory_inp), dpg.get_value(self.job_name_inp)
        )
        self.process = subprocess.Popen(
            [f"{dpg.get_value(self.ccx_name_inp)}", projekt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
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
