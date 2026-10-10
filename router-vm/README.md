# router-vm

The gateway of the lab. It plays the role of the Internet Gateway, the NAT Gateway, the route tables and the security groups of an AWS VPC. All traffic between the subnets and the internet passes through this VM.

## Details

| Item | Value |
|---|---|
| OS | Debian 13 (Trixie), no desktop environment |
| Resources | 2048 MB RAM, 2 CPU, 15 GB disk |
| Hostname | `router` |
| Packages added | `openssh-server`, `sudo`, `nftables`, `suricata` (7.0) |

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
| `etc/suricata/suricata.yaml.snippet` | `/etc/suricata/suricata.yaml` | Excerpts: monitored interface, `HOME_NET`, extra rule file (edit the existing lines, do not replace the file) |
| `etc/suricata/rules/local.rules` | `/etc/suricata/rules/local.rules` | Local rule: TCP port-scan detector |

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

- Forward chain: default drop. Allowed: established/related traffic, host to public-vm on port 80 (after DNAT), public-vm to private-vm on ports 22 (SSH) and 5432 (PostgreSQL) only, both subnets to the internet on 80/443/53 (and ICMP echo for testing).
- Input chain: still open (accept) so management access is not cut off while the lab is built.

## Intrusion detection (Suricata)

Suricata runs in IDS mode: it raises alerts and never blocks traffic. About 53,000 Emerging Threats Open rules are loaded with `suricata-update`, plus one local rule that detects TCP port scans.

Design choices:

- **Monitored interface: `enp0s8` (public-net side).** Suricata captures through AF_PACKET, which sees packets before nftables filters them, so scans that the firewall drops are still detected, with the real source address. `enp0s3` is not monitored on purpose: after NAT every internal address becomes the router's own.
- **`HOME_NET` is the private subnet (`10.0.3.0/24`).** Many rules are written as "external to home". With the default `HOME_NET` (all private ranges) every lab machine counts as "home" and those rules never match lab traffic. With the private subnet as the protected asset, public-vm counts as outside, which models a compromised web server scanning the database tier.
- **IDS only.** Blocking (IPS) is left for later, after false positives are understood.

Apply:

```
sudo apt install suricata
sudo suricata-update                                  # download the Emerging Threats Open rules
sudo cp /etc/suricata/suricata.yaml /etc/suricata/suricata.yaml.bak
# edit /etc/suricata/suricata.yaml as in etc/suricata/suricata.yaml.snippet
sudo cp etc/suricata/rules/local.rules /etc/suricata/rules/local.rules
sudo suricata -T -v -c /etc/suricata/suricata.yaml    # expect: 2 rule files processed
sudo systemctl enable --now suricata
```

Verify:

```
systemctl is-active suricata                                   # active
sudo tail -n 15 /var/log/suricata/suricata.log                 # ... Engine started (takes about 30 s)
sudo grep capture.kernel_packets /var/log/suricata/stats.log | tail -3   # packets seen, growing over time
sudo tail -f /var/log/suricata/fast.log                        # live alerts
```

Test, from public-vm:

```
sudo nmap -Pn -sS -p 1-1000 10.0.3.10
```

Expected alert in `fast.log`:

```
[1:1000001:1] LAB Possible TCP port scan [**] [Classification: Attempted Information Leak] [Priority: 2] {TCP} 10.0.1.10:38992 -> 10.0.3.10:25
```

Notes:

- Without `-Pn`, nmap reports "Host seems down": the firewall drops its discovery probes, because only ports 22 and 5432 are allowed.
- The alert targets a port that the firewall blocks, which shows that Suricata sees the packets before nftables drops them.
- The rule uses a threshold (20 SYN packets in 10 seconds per source), so one scan produces one alert, not thousands. Slow scans (for example `nmap -T1`) stay under the threshold and are not detected.

## Planned

- Tighter input chain.
- Also monitor the private-net interface (`enp0s9`); traffic crossing the subnets would then be seen twice.
- Optional: IPS mode (inline blocking) once false positives are understood.
