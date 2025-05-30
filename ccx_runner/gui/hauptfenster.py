import dearpygui.dearpygui as dpg
import subprocess
import sys
import os


class Hauptfenster:
    def __init__(self) -> None:
        self._console_out: list[str] = []
        with dpg.window(label="Example Window") as self.id:
            self.ccx_name_inp = dpg.add_input_text(
                label="Solver Name", default_value="ccx_2.19_MT"
            )
            self.job_directory_inp = dpg.add_input_text(
                label="Job Directory",
                default_value="/media/qhuss/76a9dfaf-c78f-4c2f-a48c-5a6b936cdb8d/PrePoMax/PrePoMax v2.3.4 dev/Temp/",
            )
            self.job_name_inp = dpg.add_input_text(label="Job Name", default_value="shell_solid_conn")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Run Job", callback=self.start_job)
                dpg.add_button(label="Plot Residuals")
                self.kill_job_btn = dpg.add_button(label="Stop Job", callback=self.kill_job, show=False)

            self.console_out = dpg.add_input_text(multiline=True, readonly=True, height=-1, scientific=True)

    def add_console_text(self, text: str):
        self._console_out.append(text)
        dpg.set_value(self.console_out, "".join(self._console_out))

    def kill_job(self):
        self.process.kill()
        dpg.hide_item(self.kill_job_btn)

    def start_job(self):
        dpg.show_item(self.kill_job_btn)
        self._console_out.clear()
        dpg.set_value(self.console_out, "".join(self._console_out))

        projekt = os.path.join(
            dpg.get_value(self.job_directory_inp), dpg.get_value(self.job_name_inp)
        )
        try:
            self.process = subprocess.Popen(
                [f"{dpg.get_value(self.ccx_name_inp)}", projekt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            if self.process.stdout:
                for line in self.process.stdout:
                    self.add_console_text(line)

            if self.process.stderr:
                for line in self.process.stderr:
                    print(line, file=sys.stderr, end="")  # Print errors to stderr

            return_code = self.process.wait()
            if return_code != 0:
                print(f"ccx exited with error code: {return_code}", file=sys.stderr)

        except Exception as e:
            print(e)
        dpg.hide_item(self.kill_job_btn)
