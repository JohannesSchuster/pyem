# copied from https://github.com/brisvag/cs2star/blob/master/src/cs2star/job_parser.py

import json
import re
import warnings
from pathlib import Path
from typing import Set, Iterator

class FileSet:
    def __init__(self):
        self.particles: Set[Path] = set()
        self.particles_passthrough: Set[Path] = set()
        self.micrographs: Set[Path] = set()
        self.micrographs_passthrough: Set[Path] = set()

    def __iter__(self) -> Iterator[Set[Path]]:
        yield self.particles
        yield self.particles_passthrough
        yield self.micrographs
        yield self.micrographs_passthrough

    def values(self):
        return (self.particles, self.particles_passthrough, self.micrographs, self.micrographs_passthrough)

    def values_cs(self):
        return (self.particles, self.micrographs)

    def values_passthrough(self):
        return (self.particles_passthrough, self.micrographs_passthrough)

# copied from stemia.cryosparc.csplot

class JobParser:
    SPLITJOBS = ("hetero_refine", "homo_abinit", "class_3D")
    SETJOBS   = ("particle_sets")

    def __init__(self, job_dir: str | Path):
        """
        Initialize the JobParser with a job directory and optional sets.

        :param job_dir: Path to the job directory.
        """
        self.job_dir: Path = Path(job_dir).absolute()
        self.__jobs: FileSet = FileSet()

    @property
    def jobs(self) -> FileSet: return self.__jobs

    def parse(self):
        """
        Parse the job directory to find all relevant cs files.

        This function will recursively explore the job directory and its parents
        to find all the relevant files needed for the current job.
        """
        self.__jobs = self.__find_cs_files_recursive(self.job_dir)

    def __find_cs_files_recursive(self, job_dir: Path, sets=None, visited=None) -> FileSet:
        """
        Recursively explore a job directory to find all the relevant cs files.

        This function recurses through all the parent jobs until it finds all the files
        required to have all the relevant info about the current job.
        """
        if visited is None:
            visited = []

        files: FileSet = FileSet()

        job_dir = Path(job_dir).absolute()
        try:
            with open(job_dir / "job.json") as f:
                job = json.load(f)
        except FileNotFoundError:
            warnings.warn(f'parent job "{job_dir.name}" is missing or corrupted')
            return files

        j_type = job["type"]
        for output in job["output_results"]:
            metafiles = output["metafiles"]
            passthrough = output["passthrough"]
            group = files.particles_passthrough if passthrough else files.particles
            if j_type in self.SPLITJOBS:
                # refine is special because the "good" output is split into multiple files
                if (not passthrough and "particles_class_" in output["group_name"]) or (
                    passthrough and output["group_name"] == "particles_all_classes"
                ):
                    group.add(job_dir.parent / metafiles[-1])
            elif j_type in self.SETJOBS:
                if (matched := re.search(r"split_(\d+)", output["group_name"])) is not None:
                    if sets is None or int(matched[1]) in [int(s) for s in sets]:
                        group.add(job_dir.parent / metafiles[-1])
            else:
                # every remaining job type is covered by this generic loop
                for file in metafiles:
                    if any(
                        bad in file
                        for bad in (
                            "excluded",
                            "incomplete",
                            "remainder",
                            "rejected",
                            "uncategorized",
                            "unused",
                        )
                    ):
                        continue
                    if "particles" in file:
                        group = files.particles_passthrough if passthrough else files.particles
                    elif "micrographs" in file:
                        group = files.micrographs_passthrough if passthrough else files.micrographs
                    else:
                        continue

                    group.add(job_dir.parent / file)

                for file_set in files:
                    file_set = set(sorted(file_set)[-1:])

        # remove non-existing files
        for file_set in files:
            for f in list(file_set):
                if not f.exists():
                    warnings.warn(
                        "the following file was supposed to contain relevant information, "
                        f"but does not exist:\n{f}"
                    )
                    file_set.remove(f)

        for parent in job["parents"]:
            # avoid reparsing already visited jobs
            if job["uid"] in visited:
                continue
            else:
                visited.append(job["uid"])

            self.__update_dict(self.__find_cs_files_recursive(job_dir.parent / parent, visited=visited))
            if all(files): break

        return files
    
    def __update_dict(self, d2: FileSet):
        """Recursively update nested dict."""
        # Particles
        if not self.__jobs.particles:
            self.__jobs.particles.update(d2.particles)
        if not self.__jobs.particles_passthrough:
            self.__jobs.particles_passthrough.update(d2.particles_passthrough)

        # Micrographs
        if not self.__jobs.micrographs:
            self.__jobs.micrographs.update(d2.micrographs)
        if not self.__jobs.micrographs_passthrough:
            self.__jobs.micrographs_passthrough.update(d2.micrographs_passthrough)
