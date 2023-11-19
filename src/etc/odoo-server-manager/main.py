import datetime
import hashlib
import sys
import os
import re
import subprocess

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
    # Check odoo_version with regex
    if not re.match(r"\d+\.\d+", odoo_version):
        raise ValueError("Invalid odoo_version format. Please use the format 'x.x'.")

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
    if os.path.exists("/usr/local/bin/wkhtmltopdf"):
        return
    system_architecture = platform.machine()

    if "arm" in system_architecture:
        package_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_arm64.deb"
    else:
        package_url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb"

    subprocess.run(["wget", package_url])
    subprocess.run(["sudo", "apt-get", "install", "./" + package_url.split("/")[-1], "-y"])
    subprocess.run(["sudo", "rm", package_url.split("/")[-1]])


if __name__ == "__main__":
    # first argument is the operation (list, create, delete, add_user, journal)
    # if delete, the second argument is the instance name
    # if create, the second argument is the odoo version
    if not os.path.exists("/opt/odoo"):
        subprocess.run(["sudo", "mkdir", "/opt/odoo"])
    if len(sys.argv) < 2:
        print("Please provide an operation (list, create, delete, add_user)")
        sys.exit(1)
    operation = sys.argv[1]
    if operation == "list":
        # List all instances name, version and creation date
        for instance_name in os.listdir("/opt/odoo"):
            instance_data = load_instance_data(f"{ROOT}{instance_name}/instance_data.pkl")
            print(instance_data)
    elif operation == "create":
        odoo_version = sys.argv[2]
        if len(sys.argv) >= 4:
            port = sys.argv[3]
        else:
            port = 8069
        if len(sys.argv) >= 5:
            longpolling_port = sys.argv[4]
        else:
            longpolling_port = 8072
        _install_odoo_dependencies()
        _install_wkhtmltopdf()
        create_datetime = datetime.datetime.now()
        instance_name = hashlib.md5(f"{odoo_version}-{create_datetime}".encode()).hexdigest()
        instance = OdooInstance(instance_name, odoo_version, create_datetime, port, longpolling_port)
        instance.create()
        instance.update_odoo_code()
        instance.save()
        instance.restart()
    elif operation == "delete":
        instance_name = sys.argv[2]
        print("Deleting instance...")
        subprocess.run(["sudo", "rm", "-rf", f"{ROOT}{instance_name}"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/nginx/sites-available/{instance_name}"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/nginx/sites-enabled/{instance_name}"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/systemd/system/{instance_name}.service"])
        subprocess.run(["sudo", "rm", "-rf", f"/etc/systemd/system/multi-user.target.wants/{instance_name}.service"])
        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        subprocess.run(["sudo", "systemctl", "restart", "nginx"])
        subprocess.run(["sudo", "systemctl", "restart", "postgresql"])
    elif operation == "add_user":
        instance_name = sys.argv[2]
        username = sys.argv[3]
        instance = load_instance_data(f"{ROOT}{instance_name}/instance_data.pkl")
        instance.add_user(username)
        instance.save()
    elif operation == "journal":
        instance_name = sys.argv[2]
        instance = load_instance_data(f"{ROOT}{instance_name}/instance_data.pkl")
        instance.print_journal()
