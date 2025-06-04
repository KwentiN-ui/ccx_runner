import dearpygui.dearpygui as dpg
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ccx_runner.ccx_logic.status import CalculixStatus

def run_ccx(ccx_path:Path, job_dir:Path, job_name:str, console_out:Callable, parser:Callable, finished:Optional[Callable]=None):
    """
    Runs the calculix subprocess and monitors its outputs. `parser` and `console_out` are functions that take in a single line of text.
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

    try:
        while process.poll() is None:
            if process.stdout:
                for line in process.stdout:
                    console_out(line)
                    parser(line)

            if process.stderr:
                for line in process.stderr:
                    console_out(line)
    except AttributeError:
        pass

    return_code = process.returncode if process else 0
    if return_code != 0:
        console_out(f"ccx exited with error code: {return_code}")
    if finished:
        finished()
