 # read json from file, and find all items that has regex in "include" field
import json
import re
import subprocess
import sys

def find_include():
    """
    find all items that has "include" field and has a valid regex
    """
    filename = sys.argv[1]
    with open(filename) as f:
        data = json.load(f)
    for item in data:
        # print(item.get('id'), data.index(item))
        # find all items that has "include" field and has a valid regex
        if 'include' in item and item['include']:
            try:
                re.compile(item['include'])
                print(item['include'])
            except re.error as e:
                print(f"Error: {e} in {item['include']}")
                continue


def run_checkbox_list_to_json(unit, output_file):
    """
    run "checkbox-cli list -a <unit>" and parses the input data string 
    into a list of JSON objects.

    :unit: The unit to list, e.g. "template", "job", "'test plan'", etc.
    "output_file: The output file to write the JSON objects to.

    Returns:
        A list of dictionaries representing the parsed JSON objects.
    """

    # run "checkbox-cli list -a template"
    print("Running checkbox-cli list -a " + unit)
    command = ["checkbox-cli", "list", "-a", unit]
    output = subprocess.check_output(command, universal_newlines=True)
    if not output:
        sys.exit("No output from checkbox-cli list -a "+ unit)

    unit_list = []
    current_unit = {}
    for line in output.splitlines():
    # Skip empty lines
        if not line.strip():
            continue

        # Skip the first line. New unit starts
        if line.startswith(unit.strip()):
            if current_unit:
                unit_list.append(current_unit)
                current_unit = {}
                continue
            else:
                continue

        # Extract key-value pairs (assuming colon as separator)
        key, value = line.strip().split(":", 1)
        current_unit[key.strip()] = value.strip().strip("'")  # Remove quotes

    # Add the last template if any
    if current_unit:
        unit_list.append(current_unit)

    print(f"Writing {len(unit_list)} JSON objects to file: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(unit_list, indent=4))

    return unit_list


def add_template_id_to_pxu(input_data, is_file=False):
    """
    read the json output of "checkbox-cli list -a template"
    and add template-id field to the original definition pxu file

    :input_data: The input data string or the file name containing the json list of templates 
    """
    if is_file:
        with open(input_data, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = input_data

    count = 0
    is_found = False
    for template in data:
        job_id = template['partial_id'].strip()
        template_id = template['template_id'].split('::')[-1].strip()
        origin, line_numbers = template['origin'].split(':')
        if line_numbers and "-" in line_numbers:
            start_line = int(line_numbers.split('-')[0])
            end_line = int(line_numbers.split('-')[1])
        else:
            start_line = 0
            end_line = -1
        # open the file in origin and find the line that has id
        # insert template_id to the next line as new line
        lines = []
        with open(origin, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines[start_line-1:end_line], start=start_line):
            if job_id in line:
                # print(f"Found {job_id} in {origin}, line {i}")
                is_found = True
                lines.insert(i+1, f"template-id: {template_id}\n")
                break

        if is_found:
            count += 1
        else:
            print(f"Could not find {job_id} in {origin}")
            continue

        with open(origin, 'w', encoding='utf-8') as f:
            # print(f"Processing {template_id} in {origin}")
            f.writelines(lines)

    print(f"Added {count} template-ids to the pxu files")
    return


def convert_to_template(filename):
    """
    """
    # filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines:
        if "certification-status=" in line:
            unit_id, cert_status = line.split("certification-status=")
            unit_id = unit_id.strip()
            if cert_status:
                cert_status = cert_status.strip()
            print(f"{{\"id\": \"{unit_id}\", \"cert-status\": \"{cert_status}\"}},")
        else:
            unit_id = line.strip()
            print(f"{{\"id\": \"{unit_id}\"}},")


def replace_regex_with_template_id(testplans_list, templates_list):
    """

    TODO: replace the regex in testplan-file with template_id in template-file
    
    :testplans_list: The list of testplans in json
    :templates_list: The list of templates in json
    """
    # read testplan-file
    # for each line, find the regex in list-template-file
    # replace the regex with template_id
    # write the new testplan-file
    
    not_matched = set()
    count_not_matched = 0
    count_matched = 0
    count_written = 0
    count_total = 0

    for plan in testplans_list:
        plan_id = plan['id'].split('::')[-1].strip()
        # check the `include` field in the testplan
        include = plan.get('include', '')
        if '*' not in include:
            continue

        include_items = include.split('\\n') if '\\n' in include else [include]
        print(f"Processing {plan_id} with {len(include_items)} include items")

        # find the testplan file located in origin field
        origin, line_numbers = plan['origin'].split(':')
        if line_numbers and "-" in line_numbers:
            start_line, end_line = map(int, line_numbers.split('-'))
        else:
            start_line, end_line = 0, -1
        lines = []
        with open(origin, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # check if the include item match any template 'id' field in the templates_list
        for item in include_items:
            if '*' not in item:
                continue
            count_total += 1
            # split and strip both fields
            include_str = item.strip()
            if "certification-status=" in item:
                include_str = item.split("certification-status=")[0].strip()

            matched = False
            pattern = re.compile(include_str)
            # if the include regex is for "after-suspend-", replace with the same template_id
            prefix = "after-suspend-"
            if include_str.startswith(prefix):
                pattern = re.compile(include_str[len(prefix):-1])
            # check template 'id' field in the templates_list
            for template in templates_list:
                job_id = template['partial_id'].strip()
                if not pattern.match(job_id):
                    continue

                matched = True
                count_matched += 1
                template_id = template['template_id'].split('::')[-1].strip()
                plan['include'] = plan['include'].replace(include_str, template_id)
                print(f'  Matched: {include_str} \t->\t {job_id}')
                # open the file in origin and replace the line that has id
                for i, line in enumerate(lines[start_line-1:end_line], start=start_line):
                    if include_str in line:
                        print(f"Found {job_id} in {origin}, line {i}")
                        lines[i-1] = line.replace(include_str, template_id)
                        count_written += 1
                        break

            if not matched:
                print(f"  Not matched: {include_str}")
                count_not_matched += 1
                not_matched.add(include_str)

        with open(origin, 'w', encoding='utf-8') as f:
            print(f"Writing {plan_id} in {origin}")
            f.writelines(lines)

    print("Total include:", count_total,  "Matched: ", count_matched, "Written: ", count_written)
    print("Not matched:", count_not_matched, "Dict not_matched:", len(not_matched))

    return not_matched


def main():
    """
    main function
    """
    # convert_to_template("output.log")

    template_json_file = "list-template.json"
    testplan_json_file = "list-test-plan.json"
    # run checkbox-cli
    templates_list = run_checkbox_list_to_json("template", template_json_file)
    testplans_list = run_checkbox_list_to_json("test plan", testplan_json_file)

    # is_file = True
    # if is_file:
    #     add_template_id_to_pxu(template_json_file, is_file=True)
    # else:
    #     add_template_id_to_pxu(templates_list, is_file=False)

    with open(template_json_file, 'r', encoding='utf-8') as f:
        templates_list = json.load(f)
    with open(testplan_json_file, 'r', encoding='utf-8') as f:
        testplans_list = json.load(f)
    not_matched_id_list = replace_regex_with_template_id(testplans_list, templates_list)

    with open("not_matched_id.json", 'w', encoding='utf-8') as f:
        json.dump(list(sorted(not_matched_id_list)), f, indent=4)


if __name__ == '__main__':
    main()
