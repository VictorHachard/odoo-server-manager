import os
import pickle
import subprocess
import hashlib
import datetime

from src.user import User
from src.utils import check_if_port_is_free, check_if_port_is_valid, check_if_firewall_is_enabled, get_postgres_version

ROOT = '/opt/odoo/'


def check_if_port_is_available(port):
    """
    Check if a port is available from all the odoo instances
    """
    for instance_data in load_all_instances():
        if int(instance_data.port) == int(port) or int(instance_data.longpolling_port) == int(port):
            return False
    return True


def check_port(port):
    """
    Check if a port is free, available and valid
    """
    if check_if_port_is_free(port):
        if check_if_port_is_available(port):
            if check_if_port_is_valid(port):
                return True
            else:
                print(f"Port {port} is not valid")
        else:
            print(f"Port {port} is not available")
    else:
        print(f"Port {port} is not free")
    return False


class Instance:
    def __init__(
            self,
            odoo_version: str,
            port: int = 8069,
            longpolling_port: int = 8072,
            friendly_name: str = None,
            server_name: str = None,
    ):
        self.create_datetime = datetime.datetime.now()
        self.instance_name = hashlib.md5(f"{odoo_version}-{self.create_datetime}".encode()).hexdigest()
        self.name = friendly_name
        self.odoo_version = odoo_version
        self.last_update_datetime = None
        self.port = port
        self.longpolling_port = longpolling_port
        self.server_name = server_name
        self.user = []
        self.dependencies = []
        # Check if port is free
        if not check_port(self.port):
            raise ValueError("Port is not free")
        if not check_port(self.longpolling_port):
            raise ValueError("Longpolling port is not free")
        if check_if_firewall_is_enabled():
            print("Firewall is enabled. Please add port to firewall if needed.")
        self._create()
        self.update_odoo_code()
        self.save()
        self.restart()

    def add_user(self, username):
        user = User(username)
        user.create(self.instance_name)
        self.user.append(user)

    ############################
    # Utils methods
    ############################

    def chown(self):
        subprocess.run(f"sudo chown -R {self.instance_name}:{self.instance_name} {ROOT}{self.instance_name}", shell=True)

    def _venv_exists(self):
        return os.path.exists(f"{ROOT}{self.instance_name}/venv")

    def _replace_template(self, template):
        template = template.replace("{{instance_name}}", self.instance_name)
        template = template.replace("{{create_datetime}}", self.create_datetime)
        template = template.replace("{{root}}", ROOT)
        template = template.replace("{{odoo_version}}", self.odoo_version)
        template = template.replace("{{port}}", str(self.port))
        template = template.replace("{{longpolling_port}}", str(self.longpolling_port))
        return template

    ############################
    # Update methods
    ############################

    def update_odoo_code(self):
        if os.path.exists(f"{ROOT}{self.instance_name}/update_temp"):
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/update_temp", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/update_temp", shell=True)

        if os.path.exists(f"{ROOT}{self.instance_name}/odoo_{self.odoo_version}.latest.zip"):
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/odoo_{self.odoo_version}.latest.zip", shell=True)

        if os.path.exists(f"{ROOT}{self.instance_name}/src"):
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/src", shell=True)

        wget_command = f"sudo wget https://nightly.odoo.com/{self.odoo_version}/nightly/src/odoo_{self.odoo_version}.latest.zip -P {ROOT}{self.instance_name}"
        subprocess.run(wget_command, shell=True)

        subprocess.run(f"sudo unzip -q {ROOT}{self.instance_name}/odoo_{self.odoo_version}.latest.zip -d {ROOT}{self.instance_name}/update_temp", shell=True)

        subprocess.run(f"sudo mv {ROOT}{self.instance_name}/update_temp/*/ {ROOT}{self.instance_name}/src", shell=True)

        # Copy setup/odoo to src/odoo-bin
        subprocess.run(f"sudo cp {ROOT}{self.instance_name}/src/setup/odoo {ROOT}{self.instance_name}/src/odoo-bin", shell=True)

        self.last_update_datetime = datetime.datetime.now()
        self.update_requirements()

    def update_requirements(self):
        if not self._venv_exists():
            self._create_venv()
        if os.path.exists(f"{ROOT}{self.instance_name}/src/requirements.txt"):
            subprocess.run(f"sudo -u {self.instance_name} bash -c \"source {ROOT}{self.instance_name}/venv/bin/activate && pip3 install --upgrade pip && pip3 install wheel && pip3 install -r {ROOT}{self.instance_name}/src/requirements.txt && deactivate\"", shell=True)
            for dependency in self.dependencies:
                subprocess.run(f"sudo -u {self.instance_name} bash -c \"source {ROOT}{self.instance_name}/venv/bin/activate && pip3 install --upgrade pip && pip3 install {dependency} && deactivate\"", shell=True)

    def add_dependency(self, dependency):
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)
            self.update_requirements()

    ############################
    # Create methods
    ############################

    def _create(self):
        self._create_user()
        self._create_folder_structure()
        self._create_postgresql_user()
        self._create_venv()
        self._create_odoo_config()
        self._create_service_config()
        self._create_ngnix_config()

    def _create_user(self):
        print("Creating user")
        subprocess.run(f"sudo useradd -r -s /bin/bash -d {ROOT}{self.instance_name} {self.instance_name}",
                       shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}", shell=True)

    def _create_folder_structure(self):
        if not os.path.exists(f"{ROOT}{self.instance_name}"):
            subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/src", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/logs", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/backups", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/custom_addons", shell=True)
        subprocess.run(f"sudo chmod -R 775 {ROOT}{self.instance_name}/custom_addons", shell=True)

    def _create_postgresql_user(self):
        version = get_postgres_version()
        subprocess.run(["sudo", "-u", "postgres", "createuser", "-d", "-r", "-s", self.instance_name])
        line = "/# Database administrative login by Unix domain socket/i host    all    " + self.instance_name + "    127.0.0.1/32    trust"
        subprocess.run(["sudo", "sed", "-i", line, f"/etc/postgresql/{version}/main/pg_hba.conf"])
        self.restart_postgresql()

    def _create_venv(self):
        print("Creating venv")
        self.chown()
        if self._venv_exists():
            print("Removing old venv")
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/venv", shell=True)
        subprocess.run(f"sudo -u {self.instance_name} bash -c \"python3 -m venv {ROOT}{self.instance_name}/venv\"", shell=True)

    def _create_odoo_config(self):
        print("Creating odoo config")
        if os.path.exists(f"{ROOT}{self.instance_name}/odoo.conf"):
            print("Removing old odoo config")
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/odoo.conf", shell=True)
        odoo_template = open("templates/odoo.conf", "r").read()
        odoo_template = self._replace_template(odoo_template)
        with open(f"{ROOT}{self.instance_name}/odoo.conf", "w") as f:
            f.write(odoo_template)

    def _create_service_config(self):
        print("Creating service config")
        if os.path.exists(f"/etc/systemd/system/{self.instance_name}.service"):
            print("Removing old service config")
            subprocess.run(f"sudo rm -rf /etc/systemd/system/{self.instance_name}.service", shell=True)
        service_template = open("templates/service.conf", "r").read()
        service_template = self._replace_template(service_template)
        with open(f"/etc/systemd/system/{self.instance_name}.service", "w") as f:
            f.write(service_template)
        self.enable()

    def _create_ngnix_config(self):
        print("Creating nginx config")
        if os.path.exists(f"/etc/nginx/sites-enabled/{self.instance_name}"):
            print("Removing old nginx config (enabled)")
            subprocess.run(f"sudo rm -rf /etc/nginx/sites-enabled/{self.instance_name}", shell=True)
        if os.path.exists(f"/etc/nginx/sites-available/{self.instance_name}"):
            print("Removing old nginx config (available)")
            subprocess.run(f"sudo rm -rf /etc/nginx/sites-available/{self.instance_name}", shell=True)
        server_name = f"{self.server_name};" if self.server_name else f"{self.instance_name}.example.com;"
        nginx_template = open("templates/nginx.conf", "r").read()
        nginx_template = nginx_template.replace("{{server_name}}", server_name)
        with open(f"/etc/nginx/sites-available/{self.instance_name}", "w") as f:
            f.write()
        self.enable_site()
        self.reload_nginx()

    ############################
    # Delete methods
    ############################

    def delete(self):
        version = get_postgres_version()
        command = f"sudo -u postgres psql -c 'DROP DATABASE IF EXISTS (SELECT datname FROM pg_database WHERE datdba = (SELECT usesysid FROM pg_user WHERE usename = \'{self.instance_name}\'));'"
        subprocess.run(command, shell=True)
        subprocess.run(f"sudo -u postgres dropuser {self.instance_name}", shell=True)

        line = "/host    all    " + self.instance_name + "    127.0.0.1/32    trust/d"
        subprocess.run(["sudo", "sed", "-i", line, f"/etc/postgresql/{version}/main/pg_hba.conf"])

        self.disable()
        subprocess.run(f"sudo rm -rf /etc/systemd/system/{self.instance_name}.service", shell=True)

        subprocess.run(f"sudo rm -rf /etc/nginx/sites-available/{self.instance_name}", shell=True)
        subprocess.run(f"sudo rm -rf /etc/nginx/sites-enabled/{self.instance_name}", shell=True)

        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        subprocess.run(["sudo", "systemctl", "restart", "nginx"])
        subprocess.run(["sudo", "systemctl", "restart", "postgresql"])

        subprocess.run(f"sudo userdel -r {self.instance_name}", shell=True)
        subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}", shell=True)

    ############################
    # Service methods
    ############################

    def is_running(self):
        return subprocess.run(["sudo", "systemctl", "is-active", self.instance_name + ".service"], stdout=subprocess.PIPE).returncode == 0

    def restart(self):
        subprocess.run(["sudo", "systemctl", "restart", self.instance_name + ".service"])

    def start(self):
        subprocess.run(["sudo", "systemctl", "start", self.instance_name + ".service"])

    def stop(self):
        subprocess.run(["sudo", "systemctl", "stop", self.instance_name + ".service"])

    def enable(self):
        print("Creating service symbolic link")
        subprocess.run(["sudo", "systemctl", "enable", self.instance_name + ".service"])

    def disable(self):
        subprocess.run(["sudo", "systemctl", "disable", self.instance_name + ".service"])

    def status(self):
        subprocess.run(["sudo", "systemctl", "status", self.instance_name + ".service"])

    def reload(self):
        subprocess.run(["sudo", "systemctl", "reload", self.instance_name + ".service"])

    def journal(self, lines=100, follow=False):
        if follow:
            subprocess.run(["sudo", "journalctl", "-u", self.instance_name + ".service", "-f"])
        else:
            subprocess.run(["sudo", "journalctl", "-u", self.instance_name + ".service", "-n", str(lines)])

    ############################
    # Other Service methods
    ############################

    def restart_nginx(self):
        subprocess.run(["sudo", "systemctl", "restart", "nginx"])

    def reload_nginx(self):
        subprocess.run(["sudo", "nginx", "-s", "reload"])

    def enable_site(self):
        subprocess.run(["sudo", "ln", "-s", "/etc/nginx/sites-available/" + self.instance_name, "/etc/nginx/sites-enabled/" + self.instance_name])

    def disable_site(self):
        if os.path.exists("/etc/nginx/sites-enabled/" + self.instance_name):
            subprocess.run(["sudo", "rm", "/etc/nginx/sites-enabled/" + self.instance_name])

    def restart_postgresql(self):
        subprocess.run(["sudo", "systemctl", "restart", "postgresql"])

    ############################
    # Save methods
    ############################

    def save(self):
        with open(f"{ROOT}{self.instance_name}/instance_data.pkl", "wb") as f:
            pickle.dump(self, f)

    ############################
    # Print methods
    ############################

    def __str__(self):
        return f"{self.instance_name} - {self.odoo_version} - {'Running' if self.is_running() else 'Stopped'}"

    def print_details(self):
        print(f"{self.instance_name} ({'Running' if self.is_running() else 'Stopped'}):")
        if self.name:
            print(f"    Name                 : {self.name}")
        print(f"    Instance name        : {self.instance_name}")
        print(f"    Odoo version         : {self.odoo_version}")
        print(f"    Port                 : {self.port}")
        print(f"    Longpolling port     : {self.longpolling_port}")
        print(f"    Create datetime      : {self.create_datetime}")
        print(f"    Last update datetime : {self.last_update_datetime}")
        if self.dependencies:
            print(f"    Dependencies         : {', '.join(self.dependencies)}")
        if self.user:
            print(f"    Users                : {', '.join([user.username for user in self.user])}")


def load_instance_data(instance_name):
    """ Load an instance from /opt/odoo """
    instance = None
    if os.path.isdir(f"{ROOT}{instance_name}") and os.path.exists(f"{ROOT}{instance_name}/instance_data.pkl"):
        with open(f"{ROOT}{instance_name}/instance_data.pkl", "rb") as f:
            instance = pickle.load(f)
    return instance


def load_all_instances():
    """ Load all instances from /opt/odoo """
    instances = []
    for instance_name in os.listdir(ROOT):
        instance_data = load_instance_data(f"{ROOT}{instance_name}")
        if instance_data:
            instances.append(instance_data)
    return instances
