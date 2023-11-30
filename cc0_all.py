#!/usr/bin/env python3

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import print_cmd


def transpile(perm):
    cmd = [
        "cc0",
        f"stress/recreated_{perm}.verified.c0",
        "-L",
        "src/main/resources/",
        "-L",
        "src/main/resources/",
        "--save-files",
    ]
    print_cmd(cmd)
    subprocess.run(cmd)


def main():
    perms = Path("shuffled.txt").read_text().splitlines()
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(transpile, perm): perm for perm in perms}
        for future in as_completed(futures):
            perm = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"{perm} failed: {e}")


if __name__ == "__main__":
    main()
