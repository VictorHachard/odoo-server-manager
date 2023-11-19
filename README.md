# Odoo Server Manager

This is a simple tool to manage Odoo instances on a server. It is written in Python.

## Installation

```bash
wget ....deb
```

```bash
sudo apt install ./odoo-server-manager.deb
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
