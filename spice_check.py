"""Run spice/run.cir in ngspice batch mode and return the KEY=value measurements."""
import os
import pathlib
import re
import shutil
import subprocess

HERE = pathlib.Path(__file__).parent


def ngspice():
    for exe in (os.environ.get("NGSPICE"), "ngspice", "ngspice_con"):
        if exe and (shutil.which(exe) or pathlib.Path(exe).exists()):
            return exe
    return None


def run():
    out = subprocess.run([ngspice(), "-b", "run.cir"], cwd=HERE / "spice",
                         capture_output=True, text=True, timeout=120).stdout
    return {k: float(v) for k, v in re.findall(r"^([A-Z0-9_]+)=(\S+)", out, re.M)}


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k} = {v:.6g}")
