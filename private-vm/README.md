# private-vm

The data tier. It sits in the private subnet and runs PostgreSQL with one database and one user per service. It can reach the internet outbound (updates, DNS) through the router's NAT, but nothing outside can initiate a connection to it. The only inbound paths are SSH (22) and PostgreSQL (5432), both only from public-vm.

## Details

| Item | Value |
|---|---|
| OS | Debian 13 (Trixie), no desktop environment |
| Resources | 1024 MB RAM, 1 CPU, 10 GB disk |
| Hostname | `private-vm` |
| Adapter | 1: Internal Network `private-net` |
| Address | 10.0.3.10/24 |
| Gateway | 10.0.3.1 (the router) |
| DNS | 10.0.2.3 (VirtualBox NAT DNS) |
| Packages added | `openssh-server`, `postgresql` (version 17) |

The address, gateway and DNS were entered in the Debian installer's manual network configuration. If name resolution fails, check that `/etc/resolv.conf` contains `nameserver 10.0.2.3`.

## Databases (database per service)

| Service | Database | User |
|---|---|---|
| product service | `product_db` | `product_user` |
| order service | `order_db` | `order_user` |

Each user owns its database, and `CONNECT` is revoked from `PUBLIC`, so one service's user cannot connect to the other service's database. Passwords are set interactively and are never stored in this repository.

## Files

| In this repo | Path inside the VM | Purpose |
|---|---|---|
| `etc/apt/sources.list` | `/etc/apt/sources.list` | Debian mirror lines (replaces the cdrom line left by a no-mirror install) |
| `etc/postgresql/17/main/postgresql.conf.snippet` | `/etc/postgresql/17/main/postgresql.conf` | Excerpt: `listen_addresses` (edit the existing line, do not replace the file) |
| `etc/postgresql/17/main/pg_hba.conf.snippet` | `/etc/postgresql/17/main/pg_hba.conf` | Excerpt: two rules to add after the existing ones |
| `sql/create-databases.sql` | n/a (run with psql) | Creates the users and databases (no passwords) |

## Apply

```
sudo cp etc/apt/sources.list /etc/apt/sources.list
sudo apt update
sudo apt install openssh-server postgresql

sudo -u postgres psql -f sql/create-databases.sql
sudo -u postgres psql          # then: \password product_user  and  \password order_user

# edit postgresql.conf: set listen_addresses as in the snippet (no leading #)
sudo systemctl restart postgresql

# edit pg_hba.conf: add the lines from the snippet
sudo systemctl reload postgresql
```

## Verify

```
ping -c 2 10.0.3.1              # router reachable
ping -c 2 deb.debian.org        # outbound works (NAT + DNS)
sudo apt update                 # works
sudo ss -tlnp | grep 5432       # 127.0.0.1 and 10.0.3.10 (and ::1)
sudo -u postgres psql -c "select line_number, database, user_name, address, netmask, auth_method, error from pg_hba_file_rules;"
curl -m 3 -sS http://10.0.1.10  # times out: the firewall drops private to public traffic
```

The two new `pg_hba` rules must show netmask `255.255.255.255` and an empty `error` column.

From the host, SSH access goes through the router and the bastion:

```
ssh -J <user>@192.168.56.10,<user>@10.0.1.10 <user>@10.0.3.10
```

## Planned

- Tables and data created by the services themselves (migrations).
- Backups.
