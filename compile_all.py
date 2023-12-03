#!/usr/bin/env python3

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from compile import compile


def compile_perm(perm, *, cc0, dir, prefix):
    """Compiles the given permutation with the specified compiler."""
    compile(
        src=f"stress/recreated_{perm}.verified.c0.c",
        out=f"{dir}/recreated_{perm}",
        cc0=cc0,
        prefix=prefix,
    )


def main():
    parser = argparse.ArgumentParser(
        description="./compile_all.py --cc0=$HOME/bitbucket/c0-lang/c0/cc0 --dir=o3 -- clang -O3 -fbracket-depth=1024"
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
                compile_perm, perm, cc0=args.cc0, dir=args.dir, prefix=args.cmd
            ): perm
            for perm in perms
        }
        for future in as_completed(futures):
            perm = futures[future]
            print(f"finished permutation {perm}")


if __name__ == "__main__":
    main()
