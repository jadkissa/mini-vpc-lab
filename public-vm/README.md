# public-vm

The web tier. It sits in the public subnet and runs Nginx and the application containers (Docker). It is reachable from outside only through the DNAT rule on the router (port 80), it is the bastion host for administering the private VM, and it is the only machine allowed to talk to the database.

## Details

| Item | Value |
|---|---|
| OS | Debian 13 (Trixie), no desktop environment |
| Resources | 2048 MB RAM (raised from 1024 MB to run Docker), 1 CPU, 10 GB disk |
| Hostname | `public-vm` |
| Adapter | 1: Internal Network `public-net` |
| Address | 10.0.1.10/24 |
| Gateway | 10.0.1.1 (the router) |
| DNS | 10.0.2.3 (VirtualBox NAT DNS) |
| Packages added | `openssh-server`, `nginx`, `docker.io`, `postgresql-client` |

The address, gateway and DNS were entered in the Debian installer's manual network configuration, because there is no DHCP server on the internal networks. If name resolution fails, check that `/etc/resolv.conf` contains `nameserver 10.0.2.3`.

## Files

| In this repo | Path inside the VM | Purpose |
|---|---|---|
| `etc/apt/sources.list` | `/etc/apt/sources.list` | Debian mirror lines (the install was done without a network mirror, so the cdrom line is replaced) |

## Apply

```
sudo cp etc/apt/sources.list /etc/apt/sources.list
sudo apt update
sudo apt install openssh-server nginx docker.io postgresql-client
sudo usermod -aG docker $USER      # log out and back in afterwards
```

## Verify

```
ping -c 2 10.0.1.1              # router reachable
ping -c 2 1.1.1.1               # internet through the router
ping -c 2 deb.debian.org        # DNS works
systemctl is-active nginx       # active
curl -I http://localhost        # 200 OK
docker --version                # Docker installed
ssh <user>@10.0.3.10            # bastion access to private-vm works

# database access (asks for the password of each user)
psql -h 10.0.3.10 -U product_user -d product_db   # connects
psql -h 10.0.3.10 -U product_user -d order_db     # refused: no pg_hba.conf entry
```

## Planned

- Run the two FastAPI services (product service, order service) as containers, with the database settings passed as environment variables.
- Nginx as a reverse proxy in front of the containers.
- HTTPS (port 443).
