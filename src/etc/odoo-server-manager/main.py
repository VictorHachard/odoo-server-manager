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

MAN = """Odoo Server Manager Commands:

List Instances (list):
    -d: Show details (optional).
    e.g. list -d

Create Instance (create):
    -v: Odoo version (e.g., 16.0) [required]
    -d: Odoo date (e.g., 20211010) [optional]
    -p: Port (e.g., 8069) [required]
    -l: Longpolling port (e.g., 8072) [required]
    -n: Friendly name (optional)
    -s: Server name (optional)
    -ot: Odoo template (optional)
    -st: Service template (optional)
    -nt: Nginx template (optional)
    e.g. create -v 16.0 -p 8069 -l 8072 -n odoo-16 
    e.g. create -v 16.0 -p 8069 -l 8072 -n odoo-16 -s odoo-16.example.com -ot odoo-16.conf -st odoo-16.service -nt odoo-16.nginx

Reset Instance (reset):
    -i: Instance name [required]
    -t: Type (e.g., odoo, nginx, service) [required]
    e.g. reset -i instance_name

Update Instance (update):
    -i: Instance name [required]
    -d: Odoo date (e.g., 20211010) [optional]
    e.g. update -i instance_name
    e.g. update -i instance_name -d 20211010

Add Dependency (add_dependency):
    -i: Instance name [required]
    -d: Dependency name [required]
    e.g. add_dependency -i instance_name -d Babel

Delete Instance (delete):
    -n: Instance name [required]
    e.g. delete -n instance_name

Add User (add_user):
    -i: Instance name [required]
    -u: Username [required]
    e.g. add_user -i instance_name -u admin

View Journal (journal):
    -i: Instance name [required]
    e.g. journal -i instance_name

Help (help):
    Shows this guide.
    e.g. help
"""

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

def get_system_architecture():
    architecture = platform.machine().lower()
    if "arm" in architecture:
        return "arm"
    elif any(x in architecture for x in ["amd64", "x86_64"]):
        return "amd64"
    elif "i386" in architecture:
        return "i386"
    else:
        return None

def get_ubuntu_version():
    try:
        version = subprocess.run(["lsb_release", "-cs"], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()
        return version
    except subprocess.SubprocessError:
        print("Error obtaining Ubuntu version")
        sys.exit(1)

def construct_package_url(base_repo, ubuntu_version, system_arch):
    if ubuntu_version in ["focal", "bionic", "jammy"]:
        package_url = f"{base_repo}wkhtmltox_0.12.6.1-3.{ubuntu_version}_"
    else:
        print(f"Ubuntu version '{ubuntu_version}' not supported")

    if system_arch:
        package_url += f"{system_arch}.deb"
    else:
        print("System architecture not supported")

    return package_url

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
        print("wkhtmltopdf already installed")
        return
    print("Installing wkhtmltopdf...")

    base_repo = 'https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/'
    system_arch = get_system_architecture()
    ubuntu_version = get_ubuntu_version()
    package_url = construct_package_url(base_repo, ubuntu_version, system_arch)

    subprocess.run(["wget", package_url])
    subprocess.run(["sudo", "apt-get", "install", "./" + package_url.split("/")[-1], "-y"])
    subprocess.run(["sudo", "rm", package_url.split("/")[-1]])


if __name__ == "__main__":
    error = "Please provide an operation (list, create, update, add_dependency, delete, add_user, journal, help)"
    if not os.path.exists("/opt/odoo"):
        subprocess.run(["sudo", "mkdir", "/opt/odoo"])
    if len(sys.argv) < 2:
        print(error)
        sys.exit(1)
    operation = sys.argv[1]
    if operation == "help":
        print(MAN)
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
            'd': {'value': True, 'required': False, 'type': 'str'},
            'p': {'value': True, 'required': True, 'type': 'int'},
            'l': {'value': True, 'required': True, 'type': 'int'},
            'n': {'value': True, 'required': False, 'type': 'str'},
            's': {'value': True, 'required': False, 'type': 'str'},

            'ot': {'value': True, 'required': False, 'type': 'str'},
            'st': {'value': True, 'required': False, 'type': 'str'},
            'nt': {'value': True, 'required': False, 'type': 'str'},
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
            odoo_date=args['d'] if 'd' in args else '',
            port=int(args['p']),
            longpolling_port=int(args['l']),
            server_name=args['s'] if 's' in args else '',
            odoo_template=args['ot'] if 'ot' in args else 'odoo.conf',
            service_template=args['st'] if 'st' in args else 'service.conf',
            nginx_template=args['nt'] if 'nt' in args else 'nginx.conf',
        )
    elif operation == "reset":
        args = find_args(" ".join(sys.argv[2:]), {
            'i': {'value': True, 'required': True, 'type': 'str'},
            't': {'value': True, 'required': True, 'type': 'str'},
        })
        if args['t'] not in ["odoo", "nginx", "service"]:
            print("Please provide a valid type (odoo, nginx, service)")
            sys.exit(1)
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.reset(args['t'])
        instance.restart()
    elif operation == "update":
        args = find_args(" ".join(sys.argv[2:]), {
            'i': {'value': True, 'required': True, 'type': 'str'},
            'd': {'value': True, 'required': False, 'type': 'str'},
        })
        instance = load_instance_data(args['i'])
        if not instance:
            print("Instance not found")
            sys.exit(1)
        if args['d']:
            instance.odoo_date = args['d']
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
        instance.delete()
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
