# Odoo Server Manager

Elevate your Odoo instance management on Linux servers with this nifty Python tool. It's like having a Swiss Army knife, but for Odoo servers.

## Elite Installation

First, grab the latest gadget:

```bash
wget https://github.com/VictorHachard/odoo-server-manager/releases/latest/download/odoo-server-manager.deb
```

Then, unleash it onto your system:

```bash
sudo apt install ./odoo-server-manager.deb -y
```

## Command Arsenal

### Deploying Your Troops (Create Instance)
- `-v`: Specify the Odoo version, like 16.0 (mandatory).
- `-p`: Declare the port, 8069 style (mandatory).
- `-l`: Longpolling port, say 8072 (mandatory).
- Add-ons: 
  - `-d`: Date, for a precise odoo version.
  - `-n`: Friendly name, if you're into naming your servers.
  - `-s`: Server name, for the more formal occasions.
  - `-ot`: Custom Odoo template, if you're picky.
  - `-st`: Service template, because why not?
  - `-nt`: Nginx template, for the web-savvy.

Examples:
- `odoo-server-manager create -v 16.0 -p 8069 -l 8072 -n odoo-16`
- For the fancy: `odoo-server-manager create -v 16.0 -p 8069 -l 8072 -n odoo-16 -s odoo-16.example.com -ot odoo-16.conf -st odoo-16.service -nt odoo-16.nginx`

### Reconnaissance (List Instances)
- `-d`: Details, if you're nosy (optional).
- Example: `odoo-server-manager list -d`

### Tactical Retreat (Reset Instance)
- `-i`: Instance name (mandatory).
- `-t`: Type (Odoo, nginx, or service) (mandatory).
- Example: `odoo-server-manager reset -i your_instance_name -t odoo`

### Special Ops (Update Instance)
- `-i`: Instance name (mandatory).
- `-d`: Date, for a precise odoo version.
- Example: `odoo-server-manager update -i your_instance_name`
- For the fancy: `odoo-server-manager update -i your_instance_name -d 20210501`

### Supply Drop (Add Dependency)
- `-i`: Instance name (mandatory).
- `-d`: Dependency name (mandatory).
- Example: `odoo-server-manager add_dependency -i your_instance_name -d Babel`

### Going Dark (Delete Instance)
- `-n`: Instance name (mandatory).
- Example: `odoo-server-manager delete -n your_instance_name`

### New Recruit (Add User)
- `-i`: Instance name (mandatory).
- `-u`: Username (mandatory).
- Example: `odoo-server-manager add_user -i your_instance_name -u admin`

### Black Box (View Journal)
- `-i`: Instance name (mandatory).
- Example: `odoo-server-manager journal -i your_instance_name`

### S.O.S. (Help)
- Unleash the guide.
- Example: `odoo-server-manager help`

## Ghost Protocol (Uninstallation)
When it's time to vanish:

```bash
sudo apt remove odoo-server-manager -y
```

Remember, with great power comes great responsibility. Use wisely! 🕵️‍♂️💻🚀