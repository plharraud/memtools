from typing import Literal
import json
import argparse
import pathlib
import os
import platform
import logging
import common
from pprint import pp

log = common.get_logger(logging.INFO)


supported_platforms = ["host", "guess", "linux", "windows"]
host_platform = ""


def get_path_platform(arg: str, sample_path: str = "") -> str:
    path_platform = ""

    if arg == "host":
        path_platform = platform.system().lower()
        log.info(f"using host platform: {path_platform}")

    elif arg == "guess":
        if sample_path == "":
            log.error("no sample path supplied, can not guess platform")
            path_platform = ""

        path_platform = guess_platform(sample_path)
        log.info(f"using guessed platform: {path_platform}")

    else:
        path_platform = arg
        log.info(f"using explicit platform: {path_platform}")
    return path_platform


def guess_platform(path: str) -> Literal["windows", "linux"]:
    if (":\\" in path) or (":/" in path):
        return "windows"
    return "linux"


def normalize_path(dir: str, file: str, host_platform: str) -> str:
    if host_platform == "windows":
        sourcefile = pathlib.PureWindowsPath(dir) / pathlib.PureWindowsPath(file)
        resolved = pathlib.Path(sourcefile).resolve()
        return os.path.relpath(os.path.abspath(resolved), start=os.curdir)
    elif host_platform == "linux":
        sourcefile = pathlib.PurePosixPath(dir) / pathlib.PurePosixPath(file)
        # absolute = os.path.abspath(resolved)
        return str(pathlib.Path(sourcefile).resolve())
    return ""


def parse_compile_commands(compile_commands: str, platform_arg: str):
    ret: list[dict[str, str]] = []

    with open(compile_commands, "r") as f:
        compile_commands_json = json.load(f)

        first_element_path: str = compile_commands_json[0]["directory"]

        if not first_element_path:
            log.error("malformed json")
            exit(1)

        path_platform = get_path_platform(platform_arg, first_element_path)

        if path_platform not in supported_platforms:
            log.error(f"platform {path_platform} not supported")
            exit(1)

        for o in compile_commands_json:
            source_file = normalize_path(o["directory"], o["file"], path_platform)
            object_file = normalize_path(o["directory"], o["output"], path_platform)
            root_path = os.path.commonpath([source_file, object_file])
            source_file = os.path.relpath(source_file, root_path)
            object_file = os.path.relpath(object_file, root_path)
            ret.append({"source": source_file, "object": object_file, "root": root_path})

    return ret


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("compile_commands")
    parser.add_argument(
        "-p",
        "--platform",
        choices=supported_platforms,
        default="guess",
        help="use host system, or guess using compile_commands.json paths",
    )
    args = parser.parse_args()

    paths = parse_compile_commands(args.compile_commands, args.platform)
    pp(paths)
