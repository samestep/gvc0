#!/usr/bin/env python3

import argparse
import csv
import subprocess
import time
from pathlib import Path

from common import print_cmd


def run(perm, *, dir, num_runs=30, stress=128):
    cmd = [f"{dir}/recreated_{perm}", "--stress", f"{stress}"]
    print_cmd(cmd)
    total = 0
    for _ in range(num_runs):
        start = time.perf_counter()
        try:
            subprocess.run(cmd, capture_output=True)
        except FileNotFoundError:
            print(f"binary not found")
            return None
        end = time.perf_counter()
        total += end - start
    return total / num_runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir", metavar="PATH", help="directory of binaries", required=True
    )
    parser.add_argument("--csv", metavar="PATH", help="output CSV", required=True)
    args = parser.parse_args()

    perms = Path("shuffled.txt").read_text().splitlines()
    with open(args.csv, "w") as f:
        writer = csv.DictWriter(f, fieldnames=["permutation", "seconds"])
        writer.writeheader()
        for perm in perms:
            seconds = run(perm, dir=args.dir)
            writer.writerow({"permutation": perm, "seconds": seconds})
            f.flush()


if __name__ == "__main__":
    main()
