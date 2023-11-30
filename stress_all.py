#!/usr/bin/env python3

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Regular expressions converted from Scala to Python
arbitrary_stress_declaration = re.compile(r"(int )?(stress = [0-9]+;)")
correct_stress_declaration = re.compile(
    r"(int +main\(\s*\)\s\{[\s\S]*\n\s*int stress = [0-9]+;)"
)

# The stress reading function to inject
read_stress = 'int readStress() {int* value = alloc(int); args_int("--stress", value); args_t input = args_parse(); printint(*value); return *value;}\n'


def inject_stress(source):
    # Replace the first occurrence of the correct stress declaration
    with_stress_declaration = correct_stress_declaration.sub(
        read_stress + "int main()\n{\nint stress = readStress();\nprintint(stress);\n",
        source,
        count=1,
    )

    # Remove any additional assignments to 'stress'
    removed_additional_assignments = arbitrary_stress_declaration.sub(
        "", with_stress_declaration
    )

    # Prepend additional includes
    return "#use <conio>\n#use <args>\n" + removed_additional_assignments


def modify_c0_file(perm):
    # Read the original file content
    content = Path(f"recreated/recreated_{perm}.verified.c0").read_text()

    # Inject the stress function
    content = inject_stress(content)

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
