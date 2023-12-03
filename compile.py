#!/usr/bin/env python3

import argparse
import platform
import subprocess
from pathlib import Path

from common import print_cmd

lib_ext = {"Darwin": ".dylib", "Linux": ".so"}[platform.system()]


def compile(*, src, out, cc0, prefix):
    """Compiles the given C file with the specified compiler."""
    cmd = prefix + [
        "-std=c99",
        "-g",
        "-fwrapv",
        "-Wall",
        "-Wextra",
        "-o",
        out,
        f"-I{cc0}/include",
        f"-I{cc0}/runtime",
        src,
        f"{cc0}/lib/cc0main.c",
        "-Wl,-rpath",
        f"{cc0}/lib",
        "-Wl,-rpath",
        "src/main/resources/",
        "-Wl,-rpath",
        "src/main/resources/",
        f"{cc0}/lib/libconio{lib_ext}",
        f"{cc0}/lib/libargs{lib_ext}",
        f"{cc0}/lib/libstring{lib_ext}",
        f"-L{cc0}/runtime",
        "-Wl,-rpath",
        f"{cc0}/runtime",
        f"{cc0}/runtime/libc0rt{lib_ext}",
    ]
    print_cmd(cmd)
    res = subprocess.run(cmd, capture_output=True)
    Path(f"{out}_stdout.txt").write_text(res.stdout.decode())
    Path(f"{out}_stderr.txt").write_text(res.stderr.decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc0", metavar="PATH", help="cc0 installation", required=True)
    parser.add_argument("--src", metavar="PATH", help="source file", required=True)
    parser.add_argument("--out", metavar="PATH", help="output file", required=True)
    parser.add_argument("cmd", nargs="*")
    args = parser.parse_args()

    compile(
        src=args.src,
        out=args.out,
        cc0=args.cc0,
        prefix=args.cmd,
    )


if __name__ == "__main__":
    main()
