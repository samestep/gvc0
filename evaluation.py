import os
import re
import subprocess
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def compile(recreated_number):
    cmd = ['./compile.sh', f'{recreated_number}']
    subprocess.run(cmd, capture_output=True)

def get_real_time(name, recreated_number):
    command = [f'./time.sh {name} {recreated_number}']
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    real_time = re.search(r'real\s+([0-9m.]+)s', result.stderr)
    return float(real_time.group(1).replace('m', '')) if real_time else None

def compile_all(recreated_number):
    compile(recreated_number)
    print(f"Compiled {recreated_number}.")

def time_all(recreated_number):
    before_time = get_real_time('before', recreated_number)
    after_time = get_real_time('after', recreated_number)
    difference = (1 - after_time / before_time) * 100 if before_time != 0 else None
    return {'permutation': recreated_number, 'before': before_time, 'after': after_time, 'difference': difference}

def compile_cc0_main():
    cmd = ['clang', '-fpic', '-O3', '-fbracket-depth=1024', '-std=c99', '-g', '-fwrapv', '-Wall', '-Wextra', '-pg', '-emit-llvm', '-c', '-I', '/usr/share/cc0/include', '-I', '/usr/share/cc0/runtime', '-o', 'cc0main.bc', '/usr/share/cc0/lib/cc0main.c']
    subprocess.run(cmd, capture_output=False)

def main():
    compile_cc0_main()
    files = Path("shuffled.txt").read_text().splitlines()

    # First compile them all
    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(compile_all, files)

    print("Finished compiling.")

    # Then time them all
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(time_all, files))

    # Create a DataFrame from the results and save it to a file
    df = pd.DataFrame(results)
    df.to_csv('evaluation.csv', index=False)

if __name__ == '__main__':
    main()
