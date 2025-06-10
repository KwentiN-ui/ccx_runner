import dearpygui.dearpygui as dpg
import threading
from pathlib import Path
import numpy as np
import tempfile
import json

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ccx_runner.gui.hauptfenster import Hauptfenster

from ccx_runner.ccx_logic.complex_modal.Eigenvector import Eigenvector
from ccx_runner.ccx_logic.run_ccx import run_ccx
from ccx_runner.ccx_logic.result import ResultBlock


class CampbellAnalysis:
    def __init__(self, hauptfenster: "Hauptfenster", tab_parent: int) -> None:
        self.hauptfenster = hauptfenster
        self.project_instance_data = {}
        self.plot_window = CampbellResultsWindow(self)

        self.speed_step_results: list[ComplexModalParseResult] = []

        self.speeds_tool: list[int] = []  # n, from, to

        dpg.add_text(
            'This tab provides the tools to parametrize a "*COMPLEX FREQUENCY, CORIOLIS" step,'
            " by running the analysis multiple times with different speeds. The complex frequency step gets automatically inserted if missing, but a standard frequency step as step no 3 is mandatory.",
            wrap=800,
            parent=tab_parent,
        )
        self.centrif_load_name = dpg.add_combo(
            label="Centrifugal load", parent=tab_parent
        )
        self.speeds_input = dpg.add_input_text(
            label="List of speeds [rpm]", hint="50,150,300,500.5"
        )
        with dpg.group(horizontal=True):
            dpg.add_text("Add")
            self.speeds_tool.append(
                dpg.add_input_int(
                    default_value=5,
                    width=100,
                    min_value=2,
                    min_clamped=True,
                    callback=self.callback_step_tool_triggered,
                )  # type: ignore
            )
            dpg.add_text("Steps between")
            self.speeds_tool.append(
                dpg.add_input_float(
                    default_value=0,
                    width=100,
                    min_value=0,
                    min_clamped=True,
                    callback=self.callback_step_tool_triggered,
                )  # type: ignore
            )
            dpg.add_text("and")
            self.speeds_tool.append(
                dpg.add_input_float(
                    default_value=500,
                    width=100,
                    min_value=0,
                    min_clamped=True,
                    callback=self.callback_step_tool_triggered,
                )  # type: ignore
            )

        with dpg.group(horizontal=True, parent=tab_parent):
            dpg.add_button(label="Run Analysis", callback=self.run_campbell_analysis)
            self.number_of_threads_input = dpg.add_input_int(
                default_value=3,
                label="Number of threads",
                width=100,
                min_value=1,
                min_clamped=True,
            )
            self.show_results_button = dpg.add_button(
                label="Show Results", show=False, callback=self.plot_window.show
            )
            self.save_results_button = dpg.add_button(
                label="Save results",
                show=False,
                callback=lambda: dpg.show_item(self.save_dialog),
            )

        self.tab_bar = dpg.add_tab_bar(parent=tab_parent)

        with dpg.file_dialog(
            label="Save Analysis Data",
            modal=True,
            show=False,
            default_filename="complex_frequency_results",
            callback=self.callback_confirm_save_results,
            width=800,
            height=600,
        ) as self.save_dialog:
            dpg.add_file_extension(".json", label="JSON Formatted File")

    def callback_step_tool_triggered(self):
        n, start, end = dpg.get_values(self.speeds_tool)
        dpg.set_value(
            self.speeds_input,
            ", ".join(str(round(num, 3)) for num in np.linspace(start, end, n)),
        )

    def callback_project_selected(self):
        """
        Upon selecting a project file, the available centrifugal loads are to be listed inside the corresponding combo box. 
        """
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
        """
        Returns a modified version of the provided `.inp` file, that appends a `*COMPLEX FREQUENCY, CORIOLIS`
        step to the project as a duplicate of the last `*FREQUENCY` step.
        """
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
        """
        Returns the user specified speeds to compute in [rad/s]
        """
        speeds_inp: str = dpg.get_value(self.speeds_input)
        if speeds_inp:
            # convert from rpm to rad/s
            return [rpm_to_rad_s(float(speed)) for speed in speeds_inp.split(",")]

    @property
    def modal_data(self):
        """
        Read all data from the result files, get matching eigenmodes and output their data as `(speeds[rpm]), {mode_nr:(eigenfrequency[Hz])}`
        """
        speed_results = self.speed_step_results
        speed_results.sort(key=lambda res: res.speed)

        # Step 1: Find all matching Eigenvectors that describe the same mode
        # Initialize Dictionary that holds all nodes that match the key "main" node number from the first step
        matching_modes: dict[int, list[int]] = {}
        for mode in speed_results[0].modes.values():
            matching_modes[mode.mode_nr] = [mode.mode_nr]

        for i in range(len(speed_results)):
            if i >= len(speed_results) - 1:
                continue

            res1 = speed_results[i]
            res2 = speed_results[i + 1]

            for main_mode, found_matches in matching_modes.items():
                # Get the last confirmed mode to check for a follow-up mode in the new step
                last_chain_node_nr = found_matches[-1]
                if last_chain_node_nr != -1:
                    # The chain continues
                    ref_mode = res1.modes[last_chain_node_nr]
                    for mode_nr, mode in res2.modes.items():
                        mac = ref_mode.mac(mode)
                        if mac > 0.999999:
                            found_matches.append(mode_nr)
                            break
                    else:
                        found_matches.append(-1)  # Mark the end of the chain
                else:
                    # A follow up mode from the last step could not be found. Therefore the chain was ended (denoted by -1)
                    pass

        # Step 2: Build up a data_array that can be plotted easily
        speeds = [rad_s_to_rpm(res.speed) for res in speed_results]

        freqs = {main_mode: [] for main_mode in matching_modes.keys()}
        for speedstep in speed_results:
            for main_mode, found_matches in matching_modes.items():
                freq_list = []
                for mode_no in found_matches:
                    try:
                        freq_list.append(speedstep.modes[mode_no].eigenfrequency)
                    except:
                        freq_list.append(-1)  # No valid frequency
                # If results are too short, pad them with invalid frequs
                if len(freq_list) < len(speeds):
                    freq_list += [-1] * (len(speeds) - len(freq_list))
                freqs[main_mode] = freq_list

        return speeds, freqs

    def run_cxx_limited_concurrency(self, **kwargs):
        with self.thread_pool:
            run_ccx(**kwargs)

    def run_campbell_analysis(self):
        ### Early return checks in case something is missing
        boundary_name = dpg.get_value(self.centrif_load_name)
        if boundary_name == "":
            return
        speeds = self.speeds
        if speeds is None:
            return
        dpg.hide_item(self.show_results_button)
        dpg.hide_item(self.save_results_button)

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
        for i, speed_rad_s in enumerate(speeds):
            name = f"simstep_{speed_rad_s}_{i}"
            project_dir = temp_pfad / name
            project_dir.mkdir()
            filepath = project_dir / (name + ".inp")

            # Modify speed value
            modified_project_file = inp_file.copy()
            parts = modified_project_file[line_number].split(",")
            parts[2] = str(speed_rad_s*2) # times two because PrePoMax does the same, propably because of tau/s
            modified_project_file[line_number] = ",".join(parts)

            with open(filepath, "w") as file:
                file.write("\n".join(modified_project_file))
            self.project_files.append((name, speed_rad_s, project_dir))

        # run the analysis for every subproject
        dpg.delete_item(self.tab_bar, children_only=True)
        self.project_instance_data = {}
        for name, speed_rad_s, project_dir in self.project_files:
            self.project_instance_data[name] = {}
            with dpg.tab(label=str(round(rad_s_to_rpm(speed_rad_s), 3)), parent=self.tab_bar):
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
        self.speed_step_results = []
        # Collect all the Modal Analysis result files
        for name, speed, project_dir in self.project_files:
            with open(project_dir / (name + ".frd")) as f:
                self.speed_step_results.append(
                    ComplexModalParseResult(
                        f.read(), name, speed, 3
                    )  # TODO Change hardcoded Step to something smarter
                )

        self.tempdir.cleanup()
        self.plot_window.callback_analysis_complete()
        dpg.show_item(self.show_results_button)
        dpg.show_item(self.save_results_button)

    def callback_confirm_save_results(self, sender, appdata):
        path = Path(appdata["file_path_name"])
        with open(path, "w") as f:
            data = self.modal_data
            json.dump({"speeds_rpm": data[0], "modes_hz": data[1]}, f)


class CampbellResultsWindow:
    def __init__(self, analysis: CampbellAnalysis) -> None:
        self.analysis = analysis
        with dpg.window(show=False) as self.window_id:
            with dpg.plot(width=-1, height=-1):
                dpg.add_plot_axis(
                    dpg.mvXAxis, label="revolution speed [rpm]", auto_fit=True
                )
                self.plot_axis = dpg.add_plot_axis(
                    dpg.mvYAxis, label="Eigenfrequency [Hz]"
                )

    def callback_analysis_complete(self):
        self.speeds, self.freqs = self.analysis.modal_data

    def show(self):
        dpg.show_item(self.window_id)
        dpg.delete_item(self.plot_axis, children_only=True)
        for main_mode_no, freq_list in self.freqs.items():
            dpg.add_line_series(
                tuple(  # filter out invalid frequencies
                    speed for speed, freq in zip(self.speeds, freq_list) if freq != -1
                ),
                tuple(freq for freq in freq_list if freq != -1),
                parent=self.plot_axis,
            )
        if self.analysis.speeds:
            max_speed = rad_s_to_rpm(max(self.analysis.speeds))
            for i in range(3):
                dpg.add_line_series(
                    [0, max_speed], [0, (i + 1) * max_speed], parent=self.plot_axis
                )


class ComplexModalParseResult:
    def __init__(
        self, frd_content: str, name: str, speed: float, complex_step_no: int
    ) -> None:
        self.name = name
        self.speed = speed
        self._modal_assurance_matrix: np.ndarray

        # Extract the modes from the Results file
        self.modes = {
            vec.mode_nr: vec
            for vec in Eigenvector.from_result_blocks(ResultBlock.from_frd(frd_content))
            if vec.step == complex_step_no
        }


def rad_s_to_rpm(hz: float) -> float:
    return hz * 9.5492966


def rpm_to_rad_s(rpm: float) -> float:
    return rpm * 0.1047198


def rad_s_to_rpm_array(hz: np.ndarray) -> np.ndarray:
    return rad_s_to_rpm(hz)  # type: ignore


def rpm_to_rad_s_array(rpm: np.ndarray) -> np.ndarray:
    return rpm_to_rad_s(rpm)  # type: ignore
