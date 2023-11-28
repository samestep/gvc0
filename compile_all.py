#!/usr/bin/env python3

import argparse
import platform
import subprocess
from pathlib import Path

lib_ext = {"Darwin": ".dylib", "Linux": ".so"}[platform.system()]


def compile(perm, *, cc0, cc, args):
    """Compiles the given C file with the specified compiler."""
    subprocess.run(
        [cc]
        + args
        + [
            "-std=c99",
            "-g",
            "-fwrapv",
            "-Wall",
            "-Wextra",
            "-o",
            f"{cc}/recreated_{perm}",
            f"-I{cc0}/include",
            f"-I{cc0}/runtime",
            f"recreated/recreated_{perm}.verified.c0.c",
            f"{cc0}/lib/cc0main.c",
            "-Wl,-rpath",
            f"{cc0}/lib",
            "-Wl,-rpath",
            "src/main/resources/",
            "-Wl,-rpath",
            "src/main/resources/",
            f"{cc0}/lib/libconio{lib_ext}",
            f"{cc0}/lib/libstring{lib_ext}",
            f"-L{cc0}/runtime",
            "-Wl,-rpath",
            f"{cc0}/runtime",
            f"{cc0}/runtime/libc0rt{lib_ext}",
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="./compile_all.py --cc0 $HOME/bitbucket/c0-lang/c0/cc0 --cc clang -- -O3 -fbracket-depth=512"
    )
    parser.add_argument(
        "--cc0", metavar="PATH", help="path to cc0 installation", required=True
    )
    parser.add_argument("--cc", help="C compiler", required=True)
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    perms = Path("shuffled.txt").read_text().splitlines()
    Path(args.cc).mkdir(exist_ok=True)
    for perm in perms:
        compile(perm, cc0=args.cc0, cc=args.cc, args=args.args)


if __name__ == "__main__":
    main()
