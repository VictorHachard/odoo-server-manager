import subprocess
import socket


def check_if_firewall_is_enabled() -> bool:
    """
    Check if the firewall is enabled
    """
    return subprocess.run(["sudo", "ufw", "status"], stdout=subprocess.PIPE).returncode == 0


def check_if_port_is_free(port) -> bool:
    """
    Check if a port is free
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', int(port))) != 0


def check_if_port_is_valid(port) -> bool:
    """
    Check if a port is valid
    """
    return 1024 < int(port) < 65535


def get_postgres_version() -> str:
    """
    Get the postgres version
    """
    version = subprocess.run(["psql", "--version"], stdout=subprocess.PIPE).stdout.decode("utf-8").split(" ")[2].split("\n")[0]
    return version.split(".")[0]
