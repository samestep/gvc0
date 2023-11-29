import re

def modify_c0_file(file_path):
    # Read the original file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Insert headers at the beginning
    headers = ['stress', 'conio', 'args'] 
    
    for header in headers:
        use_header = f'#use <{header}>\n'
        if not use_header in content:
            content = use_header + content

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
    content = re.sub(r'stress = [^;]+;', 'stress = readStress();', content)

    # Write the modified content back to the file
    with open(file_path[:-3] + ".modified.c0", 'w') as file:
        file.write(content)

modify_c0_file("test_modify/recreated_10.verified.c0")
modify_c0_file("test_modify/recreated_12.verified.c0")
modify_c0_file("test_modify/recreated_13.verified.c0")
modify_c0_file("test_modify/recreated_15.verified.c0")
modify_c0_file("test_modify/recreated_17.verified.c0")