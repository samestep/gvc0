#!/usr/bin/env python3

import argparse
import csv
import subprocess
import time
from pathlib import Path

from common import print_cmd

from concurrent.futures import ThreadPoolExecutor, as_completed

def run(perm, *, dir, num_runs, stress):
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


def process_permutation(perm, args):
    seconds = run(perm, dir=args.dir, num_runs=args.runs, stress=args.stress)
    with open(f"stress/recreated_{perm}.verified.time.txt", "w") as f:
        f.write(str(seconds))
        f.flush()
    return perm, seconds

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Reports the number of seconds to run each permutation.",
    )
    parser.add_argument(
        "--dir", metavar="PATH", help="directory of binaries", required=True
    )
    parser.add_argument(
        "--runs",
        metavar="N",
        type=int,
        help="number of runs per permutation",
        default=30,
    )
    parser.add_argument(
        "--stress", metavar="N", type=int, help="stress value", default=128
    )

    args = parser.parse_args()

    perms = Path("shuffled.txt").read_text().splitlines()
    with ThreadPoolExecutor(max_workers=45) as executor:
        future_to_perm = {executor.submit(process_permutation, perm, args): perm for perm in perms}

        for future in as_completed(future_to_perm):
            perm = future_to_perm[future]
            try:
                _, seconds = future.result()
            except Exception as e:
                print(f"Error processing {perm}: {e}")

if __name__ == "__main__":
    main()
