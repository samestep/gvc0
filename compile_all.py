#!/usr/bin/env python3

import argparse
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import print_cmd

lib_ext = {"Darwin": ".dylib", "Linux": ".so"}[platform.system()]


def compile(perm, *, cc0, dir, prefix):
    """Compiles the given C file with the specified compiler."""
    cmd = prefix + [
        "-std=c99",
        "-g",
        "-fwrapv",
        "-Wall",
        "-Wextra",
        "-o",
        f"{dir}/recreated_{perm}",
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
    print_cmd(cmd)
    res = subprocess.run(cmd, capture_output=True)
    Path(f"{dir}/recreated_{perm}_stdout.txt").write_text(res.stdout.decode())
    Path(f"{dir}/recreated_{perm}_stderr.txt").write_text(res.stderr.decode())


def main():
    parser = argparse.ArgumentParser(
        description="./compile_all.py --cc0=$HOME/bitbucket/c0-lang/c0/cc0 --dir=clang -- clang -O3 -fbracket-depth=1024"
    )
    parser.add_argument("--cc0", metavar="PATH", help="cc0 installation", required=True)
    parser.add_argument("--dir", metavar="PATH", help="output directory", required=True)
    parser.add_argument("cmd", nargs="*")
    args = parser.parse_args()

    perms = Path("shuffled.txt").read_text().splitlines()
    Path(args.dir).mkdir(exist_ok=True)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(
                compile, perm, cc0=args.cc0, dir=args.dir, prefix=args.cmd
            ): perm
            for perm in perms
        }
        for future in as_completed(futures):
            perm = futures[future]
            print(f"finished permutation {perm}")


if __name__ == "__main__":
    main()
