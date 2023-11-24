import subprocess
import random


class User:
    def __init__(
            self,
            username: str,
    ):
        self.username = username

    def _generate_password(self) -> str:
        return "".join(random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for i in range(16))

    def _check_ssh_password_auth(self) -> bool:
        """ Check if ssh password authentication is enabled """
        with open("/etc/ssh/sshd_config") as f:
            for line in f.readlines():
                if line.startswith("PasswordAuthentication"):
                    return line.split(" ")[1].strip() == "yes"
        return False

    def create(self, instance_name):
        new_password = self._generate_password()
        subprocess.run(f"sudo useradd -r -s /bin/bash -d {ROOT}{instance_name} {self.username}", shell=True)
        print(f"Creating user {self.username} with password {new_password}")
        if not self._check_ssh_password_auth():
            print("Password authentication is not enabled for ssh. Please enable it to be able to connect to the instance via ssh.")
        subprocess.run(f"echo {self.username}:{new_password} | sudo chpasswd", shell=True)
        subprocess.run(f"sudo usermod -a -G {instance_name} {self.username}", shell=True)

    def delete(self):
        print(f"Deleting user {self.username}")
        subprocess.run(f"sudo userdel {self.username}", shell=True)
