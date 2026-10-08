# public-vm

The web tier. It sits in the public subnet and runs Nginx (reverse proxy) and the application container (Docker). It is reachable from outside only through the DNAT rule on the router (port 80), it is the bastion host for administering the private VM, and it is the only machine allowed to talk to the database.

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

## Request path

```
host -> router (DNAT, port 80) -> Nginx :80 -> container 127.0.0.1:8000 -> PostgreSQL 10.0.3.10:5432
```

## Files

| In this repo | Path inside the VM | Purpose |
|---|---|---|
| `etc/apt/sources.list` | `/etc/apt/sources.list` | Debian mirror lines (the install was done without a network mirror, so the cdrom line is replaced) |
| `etc/nginx/sites-available/lab-api` | `/etc/nginx/sites-available/lab-api` | Reverse proxy: port 80 to the container on localhost:8000 |
| `../app/` | `~/lab-api/` | Application source, built into the `lab-api` image on this VM |
| (not in repo) | `~/lab-api.env` | `DATABASE_URL` with the real password, permissions 600 |

## Apply

```
sudo cp etc/apt/sources.list /etc/apt/sources.list
sudo apt update
sudo apt install openssh-server nginx docker.io postgresql-client
sudo usermod -aG docker $USER      # log out and back in afterwards

# Nginx site
sudo cp etc/nginx/sites-available/lab-api /etc/nginx/sites-available/lab-api
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/lab-api /etc/nginx/sites-enabled/lab-api
sudo nginx -t && sudo systemctl reload nginx

# Application (see ../app/README.md)
cd ~/lab-api
docker build -t lab-api:latest .
docker run -d --name lab-api --restart unless-stopped \
  --env-file ~/lab-api.env -p 127.0.0.1:8000:8000 lab-api:latest
```

## Verify

```
ping -c 2 10.0.1.1              # router reachable
ping -c 2 1.1.1.1               # internet through the router
ping -c 2 deb.debian.org        # DNS works
systemctl is-active nginx       # active
docker logs lab-api             # Application startup complete
curl http://localhost/healthz   # through Nginx
curl http://localhost/db-check  # database reachable
ssh <user>@10.0.3.10            # bastion access to private-vm works

# direct database access (asks for the password)
psql -h 10.0.3.10 -U app_user -d app_db -c "select * from visits;"
```

From the host: `curl http://192.168.56.10/healthz`, `curl -X POST http://192.168.56.10/visits`, `curl http://192.168.56.10/visits`.

## Planned

- Restrict which paths Nginx exposes (`/docs`, `/db-check`).
- HTTPS (port 443).
