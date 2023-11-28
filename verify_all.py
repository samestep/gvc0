#!/usr/bin/env python3

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import print_cmd


def run_task(perm):
    args = ["./run.sh", f"recreated/recreated_{perm}.c0", "--save-files"]
    print_cmd(args)
    start = time.time()
    subprocess.run(args)
    end = time.time()
    elapsed_time = end - start
    print(f"Time: {elapsed_time:.2f}s")
    return elapsed_time


def main():
    perms = Path("shuffled.txt").read_text().splitlines()

    # Define the number of threads to use
    num_threads = 4  # Adjust this based on your system capabilities

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Map the executor to the run_task function and perms
        future_to_perm = {
            executor.submit(run_task, perm): perm for perm in perms[1901:]
        }

        for future in as_completed(future_to_perm):
            perm = future_to_perm[future]
            try:
                time_taken = future.result()
                print(f"Task for {perm} completed in {time_taken:.2f} seconds")
            except Exception as e:
                print(f"Task for {perm} generated an exception: {e}")


if __name__ == "__main__":
    main()
