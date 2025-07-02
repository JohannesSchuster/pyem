import subprocess
from os import devnull
from pathlib import Path
from multiprocessing import Pool
from rich.progress import Progress

from util import get_relion_command
from normalizer import Normalizer

class Normalizer:
    def __init__(self, threads: int = 4) -> None:
        self.threads: int = threads
        self.override: bool = False
        self.output_dir: Path | None = None
        self.relion_path: str = get_relion_command("relion_preprocess")

    def setOutput(self, output_dir: str | Path, override: bool = False) -> "Normalizer":
        self.output_dir = Path(output_dir)
        self.override = override
        return self

    def normalize(
        self,
        input_dir: str | Path,
        bg_diameter: int,
        black_dust: int = -1,
        white_dust: int = -1,
    ) -> None:
        if self.output_dir is None:
            raise ValueError("Output directory not set. Use setOutput().")

        input_path = Path(input_dir)
        files: list[Path] = list(input_path.glob("*.mrcs"))
        if not files:
            raise FileNotFoundError(f"No .mrcs files found in {input_dir}")

        with Progress() as progress:
            task = progress.add_task("Normalizing", total=len(files))
            with Pool(processes=self.threads) as pool:
                for file in files:
                    pool.apply_async(self._normalize_file,
                                    (file, bg_diameter // 2, black_dust, white_dust, self.override),                                    
                                    callback=lambda _: progress.update(task, advance=1))
                pool.close()
                pool.join()

    def _normalize_file(self, args: tuple[Path, int, int, int]) -> None:
        input_file, bg_radius, black_dust, white_dust = args
        assert self.output_dir is not None  # For type checker

        output_file: Path = self.output_dir / input_file.name
        if output_file.exists() and not self.override:
            return

        cmd: list[str] = [
            self.relion_path,
            "--operate_on", str(input_file),
            "--operate_out", str(output_file),
            "--norm",
            "--bg_radius", str(bg_radius),
            "--black_dust", str(black_dust),
            "--white_dust", str(white_dust),
        ]

        with open(devnull, "w") as FNULL:
            try:
                subprocess.run(cmd, stdout=FNULL, stderr=FNULL, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed: {input_file}: {e}")