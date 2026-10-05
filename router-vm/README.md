# router-vm

The gateway of the lab. It plays the role of the Internet Gateway, the NAT Gateway, the route tables and the security groups of an AWS VPC. All traffic between the subnets and the internet passes through this VM.

## Details

| Item | Value |
|---|---|
| OS | Debian 13 (Trixie), no desktop environment |
| Resources | 2048 MB RAM, 2 CPU, 15 GB disk |
| Hostname | `router` |
| Packages added | `openssh-server`, `sudo`, `nftables` |

## Network adapters and addresses

| VirtualBox adapter | Mode | Interface | Address | Role |
|---|---|---|---|---|
| 1 | NAT | `enp0s3` | DHCP from VirtualBox (10.0.2.15) | Internet side |
| 2 | Internal Network `public-net` | `enp0s8` | 10.0.1.1/24 | Gateway of the public subnet |
| 3 | Internal Network `private-net` | `enp0s9` | 10.0.3.1/24 | Gateway of the private subnet |
| 4 | Host-Only | `enp0s10` | 192.168.56.10/24 | Management from the host, and the "outside" for the DNAT demo |

Interface names can differ on other machines. Confirm them with `ip -br a` before applying the configs.

## Files

| In this repo | Path inside the VM | Purpose |
|---|---|---|
| `etc/network/interfaces` | `/etc/network/interfaces` | Static addresses for the internal and Host-Only interfaces |
| `etc/sysctl.d/99-forward.conf` | `/etc/sysctl.d/99-forward.conf` | Enables IPv4 forwarding |
| `etc/nftables.conf` | `/etc/nftables.conf` | NAT, DNAT and the default-deny forward policy |

## Apply

```
sudo cp etc/sysctl.d/99-forward.conf /etc/sysctl.d/99-forward.conf
sudo sysctl --system

sudo cp etc/network/interfaces /etc/network/interfaces
sudo ifup enp0s8 && sudo ifup enp0s9 && sudo ifup enp0s10

sudo nft -c -f etc/nftables.conf          # syntax check first
sudo cp etc/nftables.conf /etc/nftables.conf
sudo systemctl enable --now nftables
sudo nft -f /etc/nftables.conf
```

Copying `interfaces` over an existing file replaces it, including the `enp0s3` DHCP lines, so make sure the copy in this repo matches your setup first.

## Verify

```
ip -br a                            # four interfaces with the addresses above
cat /proc/sys/net/ipv4/ip_forward   # 1
sudo nft list ruleset               # filter and nat tables present
```

From the host: `curl -I http://192.168.56.10` should return `200 OK` from Nginx on public-vm.

## Firewall behavior

- Forward chain: default drop. Allowed: established/related traffic, host to public-vm on port 80 (after DNAT), public-vm to private-vm on port 22 only, both subnets to the internet on 80/443/53 (and ICMP echo for testing).
- Input chain: still open (accept) so management access is not cut off while the lab is built.

## Planned

- Suricata in IDS mode on the internal interfaces.
- Tighter input chain.
