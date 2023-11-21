import sys
import os
import re
import subprocess
import platform

from instance import OdooInstance, load_instance_data
from __init__ import ROOT


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


def parse_args(args):
    """
    Parse the arguments and return them as a dictionary
    """
    return {(args[i]).replace('-', ''): args[i + 1] for i in range(0, len(args), 2)}


def check_args(args):
    """
    Check if the arguments are valid
    """
    if len(args) % 2 != 0:
        print("Please provide a value for each argument")
        sys.exit(1)
    for i in range(0, len(args), 2):
        if args[i].replace('-', '') not in ['v', 'n', 'p', 'l', 'i', 'u', 'd']:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)


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
    check_args(sys.argv[2:])
    args = parse_args(sys.argv[2:])
    operation = sys.argv[1]
    if operation == "help":
        print(man)
    elif operation == "list":
        details = 'd' in args
        for instance_name in os.listdir("/opt/odoo"):
            instance_data = load_instance_data(f"{ROOT}{instance_name}")
            if instance_data and details:
                instance_data.print_details()
            elif instance_data:
                print(instance_data)
    elif operation == "create":
        if 'v' not in args or 'p' not in args or 'l' not in args:
            print("Please provide an odoo_version, a port and a longpolling_port")
            sys.exit(1)
        if args['v'] not in ["16.0", "17.0"]:
            print("Please provide a valid odoo_version (16.0, 17.0)")
            sys.exit(1)
        _install_odoo_dependencies()
        _install_wkhtmltopdf()
        instance = OdooInstance(
            friendly_name=args['n'] if 'n' in args else '',
            odoo_version=args['v'],
            port=int(args['p']),
            longpolling_port=int(args['l'])
        )
        instance.create()
        instance.update_odoo_code()
        instance.save()
        instance.restart()
    elif operation == "update":
        if 'i' not in args:
            print("Please provide an instance name")
            sys.exit(1)
        instance = load_instance_data(f"{ROOT}{args['i']}")
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.update_odoo_code()
        instance.restart()
    elif operation == "add_dependency":
        if 'i' not in args:
            print("Please provide an instance name")
            sys.exit(1)
        instance = load_instance_data(f"{ROOT}{args['i']}")
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.update_requirements()
        instance.update_custom_requirements()
        instance.restart()
    elif operation == "delete":
        if 'i' not in args:
            print("Please provide an instance name")
            sys.exit(1)
        print("Deleting instance...")
        instance = load_instance_data(f"{ROOT}{args['i']}")
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
        if 'i' not in args or 'u' not in args:
            print("Please provide an instance name and a username")
            sys.exit(1)
        instance = load_instance_data(f"{ROOT}{args['i']}")
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.add_user(args['u'])
        instance.save()
    elif operation == "journal":
        if 'i' not in args:
            print("Please provide an instance name")
            sys.exit(1)
        instance = load_instance_data(f"{ROOT}{args['i']}")
        if not instance:
            print("Instance not found")
            sys.exit(1)
        instance.print_journal()
    else:
        print("Unknown operation." + error)
        sys.exit(1)
