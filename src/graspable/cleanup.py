import subprocess
from pathlib import Path


class Clean:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def clean(self):
        output_dir = Path(self.cfg["env"]["output_dir"])

        for ft in self.cfg["env"]["result_filetypes"]:
            subprocess.run(
                [f"cp *CI*{ft}* {str(output_dir)}"],
                shell=True,
                executable="/bin/bash",
                capture_output=True,
            )

        if not self.cfg["env"]["keep_log"]:
            subprocess.run(
                ["rm log/*"], shell=True, executable="/bin/bash", capture_output=True
            )

        if not self.cfg["env"]["keep_input"]:
            subprocess.run(
                ["rm input/*"], shell=True, executable="/bin/bash", capture_output=True
            )

        if not self.cfg["env"]["keep_intermediate"]:
            subprocess.run(
                ["rm *"], shell=True, executable="/bin/bash", capture_output=True
            )
