# public-vm

The web tier. It sits in the public subnet and runs the web server. It is reachable from outside only through the DNAT rule on the router (port 80), and it is the bastion host for administering the private VM.

## Details

| Item | Value |
|---|---|
| OS | Debian 13 (Trixie), no desktop environment |
| Resources | 1024 MB RAM, 1 CPU, 10 GB disk |
| Hostname | `public-vm` |
| Adapter | 1: Internal Network `public-net` |
| Address | 10.0.1.10/24 |
| Gateway | 10.0.1.1 (the router) |
| DNS | 10.0.2.3 (VirtualBox NAT DNS) |
| Packages added | `openssh-server`, `nginx` |

The address, gateway and DNS were entered in the Debian installer's manual network configuration, because there is no DHCP server on the internal networks. If name resolution fails, check that `/etc/resolv.conf` contains `nameserver 10.0.2.3`.

## Files

| In this repo | Path inside the VM | Purpose |
|---|---|---|
| `etc/apt/sources.list` | `/etc/apt/sources.list` | Debian mirror lines (the install was done without a network mirror, so the cdrom line is replaced) |

## Apply

```
sudo cp etc/apt/sources.list /etc/apt/sources.list
sudo apt update
sudo apt install openssh-server nginx
```

## Verify

```
ping -c 2 10.0.1.1              # router reachable
ping -c 2 1.1.1.1               # internet through the router
ping -c 2 deb.debian.org        # DNS works
systemctl is-active nginx       # active
curl -I http://localhost        # 200 OK
ssh <user>@10.0.3.10            # bastion access to private-vm works
```

## Planned

- The web application that talks to the database on private-vm.
- HTTPS (port 443).
