import re
import sys
import os
import subprocess
import platform
from typing import Dict, Union

from src.instance import load_instance_data, Instance, load_all_instances

ROOT = '/opt/odoo/'
PYTHON_DEPENDENCIES = [
    "build-essential",
    "python3.10",
    "python3.10-full",
    "python3-pip",
    "python3-dev",
    "python3-venv",
    "python3-wheel",
    "libxml2-dev",
    "libpq-dev",
    "libjpeg8-dev",
    "liblcms2-dev",
    "libxslt1-dev",
    "zlib1g-dev",
    "libsasl2-dev",
    "libldap2-dev",
    "libssl-dev",
    "libffi-dev",
    "libmysqlclient-dev",
    "libjpeg-dev",
    "libblas-dev",
    "libatlas-base-dev",
]


def find_args(
        input_string: str,
        rules: Dict[str, Dict[str, Union[str, bool]]],
) -> Dict[str, str]:
    """
    Finds arguments in a string based on a dictionary of rules.

    Args:
        input_string (str): The string to search.
        rules (dict): A dictionary where keys are argument names and values are dictionaries containing rules for the argument.

    Returns:
        dict: A dictionary containing the arguments and their values.

    Example:
        >>> find_args('--arg value', {'arg': {'prefix': '--', 'value': True 'required': True, 'type': 'str'}})
        {'arg': 'value'}
        >>> find_args('--arg', {'arg': {'prefix': '--', 'value': False}})
        {'arg': True}
        >>> find_args('--arg1 value1 --arg2 value2', {'arg1': {'prefix': '--', 'value': True, 'required': True, 'type': 'str'}, 'arg2': {'prefix': '--', 'value': True, 'required': True, 'type': 'str'}})
        {'arg1': 'value1', 'arg2': 'value2'}

    Raises:
        ValueError: If a required argument is not found.
    """
    args = {}
    errors = []

    for arg_name, arg_rules in rules.items():
        prefix = arg_rules.get('prefix', '-')
        value = arg_rules.get('value', False)
        required = arg_rules.get('required', False)
        type_ = arg_rules.get('type', 'str')

        if value:
            pattern = f'{prefix}{arg_name}\\s+([^\\s]+)'
        else:
            pattern = f'{prefix}{arg_name}'

        match = re.search(pattern, input_string, re.IGNORECASE)
        if match:
            if value:
                arg_value = match.group(1)
                if type_ == 'int':
                    arg_value = int(arg_value)
                elif type_ == 'float':
                    arg_value = float(arg_value)
                elif type_ == 'bool':
                    arg_value = arg_value.lower() == 'true'
                args[arg_name] = arg_value
            else:
                args[arg_name] = True
        elif required:
            errors.append(f'Argument "{arg_name}" is required.')

    if errors:
        raise ValueError('\n'.join(errors))

    return args


def _install_odoo_dependencies():
    # Check if nginx is installed
    if not os.path.exists("/etc/nginx"):
        print("Installing nginx...")
        subprocess.run(["sudo", "apt-get", "install", "nginx", "-y"])

    # Check if PostgreSQL is installed
    if not os.path.exists("/etc/postgresql"):
        print("Installing PostgreSQL...")
        subprocess.run(["sudo", "apt-get", "install", "postgresql", "-y"])

    # Check if unzip is installed
    if not os.path.exists("/usr/bin/unzip"):
        print("Installing unzip...")
        subprocess.run(["sudo", "apt-get", "install", "unzip", "-y"])

    subprocess.run(["sudo apt-get install " + " ".join(PYTHON_DEPENDENCIES) + " -y"], shell=True)


def _install_wkhtmltopdf():
    if subprocess.run(["which", "wkhtmltopdf"]).returncode == 0:
        return
    system_architecture = platform.machine()

    if "arm" in system_architecture.lower():
        package_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_arm64.deb"
    else:
        package_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb"

    subprocess.run(["wget", package_url])
    subprocess.run(["sudo", "apt-get", "install", "./" + package_url.split("/")[-1], "-y"])
    subprocess.run(["sudo", "rm", package_url.split("/")[-1]])


if __name__ == "__main__":
    error = "Please provide an operation (list, create, update, add_dependency, delete, add_user, journal, help)"
    man = """First argument is the operation (list, create, update, add_dependency, delete, add_user, journal, help)
if list:
    -d (optional)
if create:
    -v odoo_version (x.x) (required) (example: 16.0)
    -p port (required) (example: 8069)
    -l longpolling_port (required) (example: 8072)
    -n friendly_name (optional) (example: "odoo-16")
    -s server_name (optional) (example: "odoo-16.example.com")
if update:
    -i instance_name (required)
if add_dependency:
    -i instance_name (required)
    -d dependency_name (required) (example: "Babel")
if delete:
    -n instance_name (required)
if add_user: 
    -i instance_name (required)
    -u username (required) (example: admin)
if journal:
    -i instance_name (required)
"""
    if not os.path.exists("/opt/odoo"):
        subprocess.run(["sudo", "mkdir", "/opt/odoo"])
    if len(sys.argv) < 2:
        print(error)
        sys.exit(1)
    operation = sys.argv[1]
    if operation == "help":
        print(man)
    elif operation == "list":
        args = find_args(" ".join(sys.argv[2:]), {'d': {'value': False}})
        details = 'd' in args

        for instance_data in load_all_instances():
            if details:
                instance_data.print_details()
            else:
                print(instance_data)
    elif operation == "create":
        args = find_args(" ".join(sys.argv[2:]), {
            'v': {'value': True, 'required': True, 'type': 'str'},
            'p': {'value': True, 'required': True, 'type': 'int'},
            'l': {'value': True, 'required': True, 'type': 'int'},
            'n': {'value': True, 'required': False, 'type': 'str'},
            's': {'value': True, 'required': False, 'type': 'str'},
        })
        if 'v' not in args or 'p' not in args or 'l' not in args:
            print("Please provide an odoo_version, a port and a longpolling_port")
            sys.exit(1)
        if args['v'] not in ["15.0", "16.0", "17.0"]:
            print("Please provide a valid odoo_version (15.0, 16.0, 17.0)")
            sys.exit(1)
        _install_odoo_dependencies()
        _install_wkhtmltopdf()
        instance = Instance(
            friendly_name=args['n'] if 'n' in args else '',
            odoo_version=args['v'],
            port=int(args['p']),
            longpolling_port=int(args['l']),
            server_name=args['s'] if 's' in args else '',
        )
    elif operation == "update":
        args = find_args(" ".join(sys.argv[2:]), {'i': {'value': True, 'required': True, 'type': 'str'}})
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.update_odoo_code()
        instance.restart()
    elif operation == "add_dependency":
        args = find_args(" ".join(sys.argv[2:]), {
            'i': {'value': True, 'required': True, 'type': 'str'},
            'd': {'value': True, 'required': True, 'type': 'str'},
        })
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.add_dependency(args['d'])
        instance.restart()
    elif operation == "delete":
        args = find_args(" ".join(sys.argv[2:]), {'i': {'value': True, 'required': True, 'type': 'str'}})
        print("Deleting instance...")
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        for user in instance.users:
            user.delete()
        subprocess.run(["sudo", "rm", "-rf", f"{ROOT}{args['i']}"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/nginx/sites-available/{args['i']}"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/nginx/sites-enabled/{args['i']}"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/systemd/system/{args['i']}.service"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/systemd/system/multi-user.target.wants/{args['i']}.service"])
        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        subprocess.run(["sudo", "systemctl", "restart", "nginx"])
        subprocess.run(["sudo", "systemctl", "restart", "postgresql"])
    elif operation == "add_user":
        args = find_args(" ".join(sys.argv[2:]), {
            'i': {'value': True, 'required': True, 'type': 'str'},
            'u': {'value': True, 'required': True, 'type': 'str'},
        })
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.add_user(args['u'])
        instance.save()
    elif operation == "journal":
        args = find_args(" ".join(sys.argv[2:]), {'i': {'value': True, 'required': True, 'type': 'str'}})
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.print_journal()
    else:
        print("Unknown operation." + error)
        sys.exit(1)
