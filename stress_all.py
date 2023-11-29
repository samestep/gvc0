#!/usr/bin/env python3

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def modify_c0_file(perm):
    # Read the original file content
    content = Path(f"recreated/recreated_{perm}.verified.c0").read_text()

    # Insert headers at the beginning
    headers = ["stress", "conio", "args"]

    for header in headers:
        use_header = f"#use <{header}>\n"
        if not use_header in content:
            content = use_header + content

    # Add the updated readStress method before main()
    read_stress_method = (
        "int readStress() {\n"
        "    int* value = alloc(int); \n"
        '    args_int("--stress", value); \n'
        "    args_t input = args_parse(); \n"
        "    return *value;\n"
        "}\n\n"
    )
    content = re.sub(r"(?=int main\(\))", read_stress_method, content)

    # Replace the first occurrence of int stress = <expression>;
    content = re.sub(r"stress = [^;]+;", "stress = readStress();", content)

    # Write the modified content to a new file
    Path(f"stress/recreated_{perm}.verified.c0").write_text(content)


def main():
    perms = Path("shuffled.txt").read_text().splitlines()
    Path("stress").mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(modify_c0_file, perm): perm for perm in perms}
        for future in as_completed(futures):
            perm = futures[future]
            try:
                future.result()
                print(f"{perm} succeeded")
            except Exception as e:
                print(f"{perm} failed: {e}")


if __name__ == "__main__":
    main()
