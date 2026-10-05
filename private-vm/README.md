# private-vm

The data tier. It sits in the private subnet. It can reach the internet outbound (updates, DNS) through the router's NAT, but nothing outside can initiate a connection to it. The only inbound path is SSH (port 22) from public-vm, which acts as the bastion.

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
| Packages added | `openssh-server` |

The address, gateway and DNS were entered in the Debian installer's manual network configuration. If name resolution fails, check that `/etc/resolv.conf` contains `nameserver 10.0.2.3`.

## Files

| In this repo | Path inside the VM | Purpose |
|---|---|---|
| `etc/apt/sources.list` | `/etc/apt/sources.list` | Debian mirror lines (the install was done without a network mirror, so the cdrom line is replaced) |

## Apply

```
sudo cp etc/apt/sources.list /etc/apt/sources.list
sudo apt update
sudo apt install openssh-server
```

## Verify

```
ping -c 2 10.0.3.1              # router reachable
ping -c 2 deb.debian.org        # outbound works (NAT + DNS)
sudo apt update                 # works
curl -m 3 -sS http://10.0.1.10  # times out: the firewall drops private to public traffic
```

From the host, access goes through the router and the bastion:

```
ssh -J <user>@192.168.56.10,<user>@10.0.1.10 <user>@10.0.3.10
```

## Planned

- PostgreSQL, listening on 10.0.3.10 only.
- Decision for Phase 7: open the database port from public-vm only, or use an SSH tunnel.
