import dearpygui.dearpygui as dpg
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ccx_runner.ccx_logic.status import CalculixStatus


def run_ccx(
    ccx_path: Path,
    job_dir: Path,
    job_name: str,
    process_holder: Optional[object] = None,
    console_out: Optional[Callable] = None,
    parser: Optional[Callable] = None,
    finished: Optional[Callable] = None,
    identifier: Optional[str] = None,
):
    """
    Runs the calculix subprocess and monitors its outputs. `parser` and `console_out` are functions that take in a single line of text, aswell as an identifier string.
    The `finished` function will get called at the end.
    """

    process = subprocess.Popen(
        [f"{ccx_path.resolve()}", f"{job_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=job_dir.resolve(),
    )
    if process_holder:
        process_holder.process = process # type: ignore
    try:
        while process.poll() is None:
            if process.stdout:
                for line in process.stdout:
                    if console_out:
                        console_out(line, identifier)
                    if parser:
                        parser(line, identifier)

            if process.stderr:
                for line in process.stderr:
                    if console_out:
                        console_out(line, identifier)
    except AttributeError:
        pass

    return_code = process.returncode if process else 0
    if return_code != 0:
        if console_out:
            console_out(f"ccx exited with error code: {return_code}", identifier)
    if finished:
        finished(identifier)
