# Odoo Server Manager

This is a simple python tool to manage Odoo instances on a linux server.

## Installation

```bash
wget https://github.com/VictorHachard/odoo-server-setup/releases/latest/download/odoo-server-manager.deb
```

```bash
sudo apt install ./odoo-server-manager.deb -y
```

## Usage

```bash
odoo-server-manager create -v <odoo_version> -p <port> -l <longpolling_port>
```

```bash
odoo-server-manager list
```

```bash
odoo-server-manager update -i <instance_name>
```

```bash
odoo-server-manager delete -i <instance_name>
```

```bash
odoo-server-manager journal -i <instance_name>
```

## Uninstallation

```bash
sudo apt remove odoo-server-manager -y
```
