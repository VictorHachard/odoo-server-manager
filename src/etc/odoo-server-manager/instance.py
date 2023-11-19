import os
import hashlib
import datetime
import os
import hashlib
import datetime
import pickle
import platform
import re
import subprocess
import sys
import random

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
ROOT = '/opt/odoo/'


def check_if_port_is_free(port):
    """
    Check if a port is free
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0


def check_if_port_is_available(port):
    """
    Check if a port is available from all the odoo instances
    """
    for instance_name in os.listdir("/opt/odoo"):
        instance_data = load_instance_data(f"{ROOT}{instance_name}/instance_data.pkl")
        if instance_data.port == port or instance_data.longpolling_port == port:
            return False
    return True


def check_if_port_is_valid(port):
    """
    Check if a port is valid
    """
    return 1024 < port < 65535


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


class User:
    def __init__(self, odoo_instance, username):
        self.odoo_instance = odoo_instance
        self.username = username

    def _generate_password(self):
        return "".join(random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for i in range(16))

    def create(self):
        """
        Create a user for the instance with password
        """
        new_password = self._generate_password()
        print(f"Creating user {self.username} with password {new_password}")
        subprocess.run(f"sudo useradd -r -s /bin/bash -d {ROOT}{self.odoo_instance.instance_name} {self.username}", shell=True)
        subprocess.run(f"echo '{new_password}' | sudo passwd --stdin {self.username}", shell=True)
        subprocess.run(f"sudo usermod -a -G {self.odoo_instance.instance_name} {self.username}", shell=True)


class OdooInstance:
    def __init__(self, instance_name, odoo_version, create_datetime, port=8069, longpolling_port=8072):
        self.instance_name = instance_name
        self.odoo_version = odoo_version
        self.create_datetime = create_datetime
        self.port = port
        self.longpolling_port = longpolling_port
        self.user = []
        # Check if port is free
        if not check_port(self.port):
            raise ValueError("Port is not free")
        if not check_port(self.longpolling_port):
            raise ValueError("Longpolling port is not free")

    def add_user(self, username):
        user = User(self, username)
        user.create()
        self.user.append(user)

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

        self.update_requirements()

    def update_requirements(self):
        if not self._venv_exists():
            self.create_venv()
        if os.path.exists(f"{ROOT}{self.instance_name}/src/requirements.txt"):
            subprocess.run(f"sudo -u {self.instance_name} bash -c \"source {ROOT}{self.instance_name}/venv/bin/activate && pip3 install --upgrade pip && pip3 install wheel && pip3 install -r {ROOT}{self.instance_name}/src/requirements.txt && deactivate\"", shell=True)

    def chown(self):
        subprocess.run(f"sudo chown -R {self.instance_name}:{self.instance_name} {ROOT}{self.instance_name}", shell=True)

    def _venv_exists(self):
        return os.path.exists(f"{ROOT}{self.instance_name}/venv")

    def create(self):
        self.create_user()
        self.create_folder_structure()
        self.create_postgresql_user()
        self.create_venv()
        self.create_odoo_config()
        self.create_service_config()
        self.create_ngnix_config()

    def create_folder_structure(self):
        if not os.path.exists(f"{ROOT}{self.instance_name}"):
            subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/src", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/logs", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/backups", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}/custom_addons", shell=True)

    def create_postgresql_user(self):
        subprocess.run(["sudo", "-u", "postgres", "createuser", "-d", "-r", "-s", self.instance_name])
        line = "/# Database administrative login by Unix domain socket/i host    all    " + self.instance_name + "    127.0.0.1/32    trust"
        subprocess.run(["sudo", "sed", "-i", line, "/etc/postgresql/14/main/pg_hba.conf"])
        subprocess.run(["sudo", "systemctl", "restart", "postgresql"])

    def create_venv(self):
        print("Creating venv")
        self.chown()
        if self._venv_exists():
            print("Removing old venv")
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/venv", shell=True)
        subprocess.run(f"sudo -u {self.instance_name} bash -c \"python3 -m venv {ROOT}{self.instance_name}/venv\"", shell=True)

    def create_user(self):
        print("Creating user")
        subprocess.run(f"sudo useradd -r -s /bin/bash -d {ROOT}{self.instance_name} {self.instance_name}", shell=True)
        subprocess.run(f"sudo mkdir {ROOT}{self.instance_name}", shell=True)

    def create_ngnix_config(self):
        print("Creating nginx config")
        if os.path.exists(f"/etc/nginx/sites-enabled/{self.instance_name}"):
            print("Removing old nginx config (enabled)")
            subprocess.run(f"sudo rm -rf /etc/nginx/sites-enabled/{self.instance_name}", shell=True)
        if os.path.exists(f"/etc/nginx/sites-available/{self.instance_name}"):
            print("Removing old nginx config (available)")
            subprocess.run(f"sudo rm -rf /etc/nginx/sites-available/{self.instance_name}", shell=True)

        nginx_config_file = f"/etc/nginx/sites-available/{self.instance_name}"
        with open(nginx_config_file, "w") as f:
            f.write(f"""#server {{
#  listen 80;
#  listen [::]:80;
#  server_name $WEBSITE_NAME;
#  return 301 https://\$host\$request_uri;
#}}

server {{
    listen 80;
    #listen 443 ssl http2;
    #listen [::]:443 ssl http2;
    #ssl_certificate ;
    #ssl_certificate_key ;
    server_name {self.instance_name}.example.com;

    root /var/www/html;

    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Real-IP \$remote_addr;
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    proxy_set_header X-Client-IP \$remote_addr;
    proxy_set_header HTTP_X_FORWARDED_HOST \$remote_addr;

    access_log /var/log/nginx/{self.instance_name}.access.log;
    error_log /var/log/nginx/{self.instance_name}.error.log;

    location / {{
        proxy_pass http://localhost:{self.port};
        proxy_redirect off;
        proxy_max_temp_file_size 0;
    }}

    location /longpolling {{
        proxy_pass http://localhost:{self.longpolling_port};
        proxy_redirect off;
        proxy_max_temp_file_size 0;
    }}

    location ~* .(js|css)$ {{
        expires 2d;
        proxy_pass http://localhost:{self.port};
        add_header Cache-Control "public, no-transform";
    }}

    location ~* .(jpg|jpeg|png|gif|ico)$ {{
        expires 14d;
        proxy_pass http://localhost:{self.port};
        add_header Cache-Control "public, no-transform";
    }}
""")
        print("Creating nginx symbolic link")
        os.symlink(nginx_config_file, f"/etc/nginx/sites-enabled/{self.instance_name}")

    def create_odoo_config(self):
        print("Creating odoo config")
        if os.path.exists(f"{ROOT}{self.instance_name}/odoo.conf"):
            print("Removing old odoo config")
            subprocess.run(f"sudo rm -rf {ROOT}{self.instance_name}/odoo.conf", shell=True)
        with open(f"{ROOT}{self.instance_name}/odoo.conf", "w") as f:
            f.write(f"""[options]
addons_path = {ROOT}{self.instance_name}/src/addons, {ROOT}{self.instance_name}/custom_addons
logfile = {ROOT}{self.instance_name}/logs/odoo.log
db_host = localhost
db_port = 5432
db_user = {self.instance_name}
db_password = {self.instance_name}
db_name = {self.instance_name}
http_port = {self.port}
longpolling_port = {self.longpolling_port}
""")

    def create_service_config(self):
        print("Creating service config")
        if os.path.exists(f"/etc/systemd/system/{self.instance_name}.service"):
            print("Removing old service config")
            subprocess.run(f"sudo rm -rf /etc/systemd/system/{instance_name}.service", shell=True)
        with open(f"/etc/systemd/system/{self.instance_name}.service", "w") as f:
            f.write(f"""[Unit]
Description=Odoo Instance {self.instance_name}
Requires=postgresql.service
After=network.target postgresql.service

[Service]
Type=simple
SyslogIdentifier={self.instance_name}
PermissionsStartOnly=true
ExecStart={ROOT}{self.instance_name}/venv/bin/python {ROOT}{self.instance_name}/src/odoo-bin -c {ROOT}{self.instance_name}/odoo.conf
User={self.instance_name}
Group={self.instance_name}
Restart=always

[Install]
WantedBy=multi-user.target
""")
        print("Creating service symbolic link")
        os.symlink(f"/etc/systemd/system/{self.instance_name}.service", f"/etc/systemd/system/multi-user.target.wants/{self.instance_name}.service")

    def save(self):
        with open(f"{ROOT}{self.instance_name}/instance_data.pkl", "wb") as f:
            pickle.dump(self, f)

    def __str__(self):
        return f"{self.instance_name} - {self.odoo_version} - {self.port} - {self.longpolling_port} - {self.create_datetime}"


def load_instance_data(file_path):
    with open(file_path, "rb") as f:
        instance = pickle.load(f)
    return instance


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
    # first argument is the operation (list, create, delete)
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
        _install_odoo_dependencies()
        _install_wkhtmltopdf()
        create_datetime = datetime.datetime.now()
        instance_name = hashlib.md5(f"{odoo_version}-{create_datetime}".encode()).hexdigest()
        instance = OdooInstance(instance_name, odoo_version, create_datetime)
        instance.create()
        instance.update_odoo_code()
        instance.save()
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
