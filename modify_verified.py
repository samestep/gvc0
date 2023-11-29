import re

def modify_c0_file(file_path):
    # Read the original file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Insert headers at the beginning
    headers = '#use <stress>\n#use <conio>\n#use <args>\n'
    content = headers + content

    # Add the updated readStress method before main()
    read_stress_method = (
        'int readStress() {\n'
        '    int* value = alloc(int); \n'
        '    args_int("--stress", value); \n'
        '    args_t input = args_parse(); \n'
        '    return *value;\n'
        '}\n\n'
    )
    content = re.sub(r'(?=int main\(\))', read_stress_method, content)

    # Replace the first occurrence of int stress = <expression>;
    content = re.sub(r'int stress = [^;]+;', 'int stress = readStress();', content)

    # Write the modified content back to the file
    with open(file_path[:-2] + ".modified.c0", 'w') as file:
        file.write(content)

