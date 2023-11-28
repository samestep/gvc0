import csv
import os
import subprocess
import time

def compile_and_run(compiler, c_file, num_runs=30):
    """Compiles the given C file with the specified compiler and measures execution time."""
    compile_command = f"{compiler} -std=c99 -g -fwrapv -Wall -Wextra -o a.out -I/usr/share/cc0/include " \
                      f"-I/usr/share/cc0/runtime recreated/{c_file} /usr/share/cc0/lib/cc0main.c " \
                      f"-Wl,-rpath /usr/share/cc0/lib -Wl,-rpath src/main/resources " \
                      f"-Wl,-rpath src/main/resources /usr/share/cc0/lib/libconio.so " \
                      f"/usr/share/cc0/lib/libstring.so -L/usr/share/cc0/runtime " \
                      f"-Wl,-rpath /usr/share/cc0/runtime /usr/share/cc0/runtime/libc0rt.so"
    try:
        # Compile the program
        subprocess.run(compile_command, shell=True, check=True)

        total_time = 0

        # Run the program multiple times and calculate the average execution time
        for _ in range(num_runs):
            start_time = time.perf_counter()
            subprocess.run("./a.out", shell=True, check=True)
            end_time = time.perf_counter()
            total_time += end_time - start_time

        return total_time / num_runs

    except subprocess.CalledProcessError:
        # Return None if compilation or execution fails
        return None

def compile_and_measure_performance(c_files, csv_file, error_file):

    """Compiles and measures the performance of given C files with gcc and clang."""
    with open(csv_file, 'w', newline='') as file, open(error_file, 'w') as error_file:
        writer = csv.DictWriter(file, fieldnames=["Filename", "GCC Time", "Clang Time", "Difference Time"])
        writer.writeheader()

        for c_file in c_files:
            gcc_time = compile_and_run("gcc", c_file)
            clang_time = compile_and_run("clang -O3 -fbracket-depth=512", c_file)

            # Check for errors in compilation or execution
            if gcc_time is None or clang_time is None:
                error_file.write(c_file + '\n')
                error_file.flush()
                continue

            result = {
                "Filename": c_file[:-14],
                "GCC Time": gcc_time,
                "Clang Time": clang_time,
                "Difference Time": abs(gcc_time - clang_time)
            }

            writer.writerow(result)
            file.flush()

def get_c_files(directory):
    """Returns a list of .c files in the given directory."""
    return [file for file in os.listdir(directory) if file.endswith('.c')]

c_files = sorted(get_c_files("recreated"), key = lambda x: int(x.split('_')[1].split('.')[0]))
compile_and_measure_performance(c_files, "compilation_results.csv", "compilation_errors.txt")