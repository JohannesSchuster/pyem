import os
import sys
import argparse
from pathlib import Path
from normalizer import Normalizer


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