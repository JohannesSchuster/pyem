import argparse
import subprocess
from multiprocessing import Pool
import sys
import shutil
import os
from pathlib import Path
from rich.progress import Progress

class Normalizer:
    def __init__(self, threads: int = 4) -> None:
        self.threads: int = threads
        self.override: bool = False
        self.output_dir: Path | None = None
        relion_path = shutil.which("relion_preprocess")
        if relion_path is None:
            raise EnvironmentError("relion_preprocess not found in PATH.")
        self.relion_path: str = relion_path

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

        with open(os.devnull, "w") as FNULL:
            try:
                subprocess.run(cmd, stdout=FNULL, stderr=FNULL, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed: {input_file}: {e}")

def main(args: argparse.Namespace):
    if not args.input or not args.input[0]:
        print("No input directory given")
        return 1
    input_path = Path(args.input[0])
    if not input_path.exists() or not input_path.is_dir():
        print(f"Input path '{input_path}' does not exist or is not a directory.")
        return 1
    output: Path = Path(args.output or os.path.join(os.getcwd(), "picks"))
    output.mkdir(parents=True, exist_ok=True)

    normalizer = Normalizer(threads=os.cpu_count() or 4)
    normalizer.setOutput(output, True if args.override else False)

    try:
        normalizer.normalize(
            input_dir=input_path,
            bg_diameter=args.bg_diameter,
            black_dust=args.black_dust or -1,
            white_dust=args.white_dust or -1,
        )
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1
    except:
        print("[ERROR] An unexpected error occurred.")
        return 1
    
def _main_():
    parser = argparse.ArgumentParser(
        description=(
            "Normalize .mrcs particle stacks using relion_preprocess.\n"
            "The input has to be the directory, where the stacks are stored.\n"
            "The output will be written to the specified output directory.\n"
            "If no output directory is given, it will be created in the current working directory."
            ""
            "Written by J. Schuster (Univerity of Regensburg, Germany)"
        )
    )
    parser.add_argument("input", help="Directory, with the particle-stacks", nargs="*")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--bg_diameter", help="Diameter of the background circle", type=int)
    parser.add_argument("--bg_diameter", help="Diameter of the background circle", type=int)
    parser.add_argument("--bg_diameter", help="Diameter of the background circle", type=int)
    parser.add_argument("--force", help="Force overwrite existing files", action="store_true")
    sys.exit(main(parser.parse_args()))

if __name__ == "__main__":
    _main_()