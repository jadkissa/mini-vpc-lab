# Setup guide

Step-by-step instructions for building the lab. Replace `<user>` with your own Linux username.

## 0. Prerequisites

- VirtualBox installed on the host
- Debian netinst ISO (amd64), Debian 13 "Trixie"
- About 8 GB of free RAM for the three VMs

## 1. Plan the addresses

Write the plan down first (see the addressing table in the README). Keep the private subnet away from 10.0.2.0/24, which VirtualBox uses for its NAT network.

## 2. Create the router VM

VirtualBox settings:

| Setting | Value |
|---|---|
| Name / type | `router`, Linux, Debian (64-bit) |
| RAM / CPU / disk | 2048 MB / 2 / 15 GB |
| Adapter 1 | NAT |
| Adapter 2 | Internal Network `public-net` |
| Adapter 3 | Internal Network `private-net` |
| Adapter 4 | Host-Only Adapter (create the network first, see section 5) |

On adapters 2 and 3, set Promiscuous Mode to "Allow All" (needed later for the IDS).

Debian installer choices:

- Hostname: `router`
- Leave the root password empty. The installer then disables root login and installs `sudo` for your user.
- Software selection: untick every desktop environment (including the main "Debian desktop environment" entry). Keep only **SSH server** and **standard system utilities**.

After the first boot, check the interfaces:

```
ip -br a
ping -c 2 deb.debian.org
```

Expected: three interfaces besides `lo` (typically `enp0s3`, `enp0s8`, `enp0s9`, plus `enp0s10` once adapter 4 is enabled). `enp0s3` gets an address from VirtualBox's DHCP.

## 3. Router networking

### 3.1 Static addresses for the internal interfaces

Edit `/etc/network/interfaces` and add (keep the existing loopback and `enp0s3` DHCP lines):

```
auto enp0s8
iface enp0s8 inet static
        address 10.0.1.1/24

auto enp0s9
iface enp0s9 inet static
        address 10.0.3.1/24
```

Apply:

```
sudo ifup enp0s8
sudo ifup enp0s9
ip -br a
```

No `gateway` lines here: the router already has a default route through `enp0s3`.

### 3.2 IP forwarding

```
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-forward.conf
sudo sysctl --system
cat /proc/sys/net/ipv4/ip_forward
```

The last command should print `1`.

### 3.3 NAT with nftables

```
sudo apt install nftables
sudo systemctl enable --now nftables
```

Use the ruleset in [`router-vm/etc/nftables.conf`](../router-vm/etc/nftables.conf). Always check the syntax before applying:

```
sudo nft -c -f /etc/nftables.conf
sudo nft -f /etc/nftables.conf
sudo nft list ruleset
```

## 4. Create the public VM and the private VM

Create both VMs with 1024 MB RAM (public-vm is raised to 2048 MB later, see section 9), 1 CPU, 10 GB disk and a single adapter:

| VM | Adapter 1 |
|---|---|
| public-vm | Internal Network `public-net` |
| private-vm | Internal Network `private-net` |

There is no DHCP server on the internal networks, so the Debian installer will ask for manual network settings:

| Field | public-vm | private-vm |
|---|---|---|
| IP address | 10.0.1.10 | 10.0.3.10 |
| Netmask | 255.255.255.0 | 255.255.255.0 |
| Gateway | 10.0.1.1 | 10.0.3.1 |
| Name server | 10.0.2.3 | 10.0.2.3 |

`10.0.2.3` is VirtualBox's built-in DNS for NAT networks. Public DNS servers (1.1.1.1, 8.8.8.8) did not answer from behind the router in this setup, see the troubleshooting page.

If the installer cannot reach a mirror (or skips the software selection screen), continue with "No network mirror". After the first boot:

1. Edit `/etc/apt/sources.list`: comment out the `deb cdrom:` line and add the lines from [`public-vm/etc/apt/sources.list`](../public-vm/etc/apt/sources.list).
2. Install the SSH server:

```
sudo apt update
sudo apt install openssh-server
```

3. On public-vm, install the web server:

```
sudo apt install nginx
curl -I http://localhost
```

4. If name resolution fails on a VM, check `/etc/resolv.conf`. It should contain `nameserver 10.0.2.3`.

Verify from each VM:

```
ping -c 2 <its gateway>
ping -c 2 1.1.1.1
ping -c 2 deb.debian.org
```

## 5. Host-Only adapter and SSH from the host

1. In VirtualBox, create a Host-Only network (Tools > Network, Host-only Networks, Create). Typical range: 192.168.56.0/24, with the host at 192.168.56.1.
2. Select it on the router's adapter 4.
3. Add to `/etc/network/interfaces` on the router:

```
auto enp0s10
iface enp0s10 inet static
        address 192.168.56.10/24
```

4. Apply with `sudo ifup enp0s10`, then from the host:

```
ssh <user>@192.168.56.10
```

Using the router as a jump host:

```
ssh -J <user>@192.168.56.10 <user>@10.0.1.10
ssh -J <user>@192.168.56.10,<user>@10.0.1.10 <user>@10.0.3.10
```

## 6. Publish the web app through the router (DNAT)

The `prerouting` chain in the nat table forwards port 80 arriving on the Host-Only interface to the public VM. It is part of [`router-vm/etc/nftables.conf`](../router-vm/etc/nftables.conf).

Test from the host:

```
curl -I http://192.168.56.10
```

Expected: `HTTP/1.1 200 OK` from Nginx on public-vm.

## 7. Security groups (firewall policy)

The forward chain uses `policy drop` with explicit allows (see the README for the policy table). Apply it safely:

1. Write the ruleset to a temporary file, check it with `sudo nft -c -f <file>`, then load it live with `sudo nft -f <file>`.
2. Test everything (table below).
3. Only then copy it to `/etc/nftables.conf` so it survives reboots.

The input chain stays open while building the lab so an error does not lock you out of the router.

### Tests

| From | Test | Expected |
|---|---|---|
| Host | `curl -I http://192.168.56.10` | `200 OK` |
| public-vm | `ssh <user>@10.0.3.10` | Login works |
| public-vm | `curl -m 3 -sS http://10.0.3.10` | Times out (dropped, not refused) |
| private-vm | `sudo apt update` | Works (outbound NAT) |
| private-vm | `curl -m 3 -sS http://10.0.1.10` | Times out (dropped) |

## 8. PostgreSQL on private-vm

Install PostgreSQL and create a database and a dedicated user for the application. The SQL is in [`private-vm/sql/create-databases.sql`](../private-vm/sql/create-databases.sql). Set the password interactively so it never appears in files or shell history:

```
sudo apt install postgresql
sudo -u postgres psql -f create-databases.sql
sudo -u postgres psql
```

Inside `psql`: `\password app_user`, then check with `\l` and `\du`.

### 8.1 Listen on the private address

In `/etc/postgresql/17/main/postgresql.conf` (see the [snippet](../private-vm/etc/postgresql/17/main/postgresql.conf.snippet)) set, without a leading `#`:

```
listen_addresses = 'localhost,10.0.3.10'
```

```
sudo systemctl restart postgresql
sudo ss -tlnp | grep 5432
```

Expected: `127.0.0.1:5432` and `10.0.3.10:5432` (plus `[::1]:5432`, which is local only).

### 8.2 Who may connect (`pg_hba.conf`)

Add the line from the [snippet](../private-vm/etc/postgresql/17/main/pg_hba.conf.snippet) after the existing rules. The user is limited to its own database and to the public VM (`/32` means a single host).

```
sudo systemctl reload postgresql
sudo -u postgres psql -c "select line_number, database, user_name, address, netmask, auth_method, error from pg_hba_file_rules;"
```

The `error` column must be empty and the netmask of the new rule must be `255.255.255.255`.

### 8.3 Firewall

Allow PostgreSQL from the public VM only. The rule is in the forward chain of [`router-vm/etc/nftables.conf`](../router-vm/etc/nftables.conf):

```
iifname "enp0s8" oifname "enp0s9" ip saddr 10.0.1.10 ip daddr 10.0.3.10 tcp dport 5432 accept
```

```
sudo nft -c -f /etc/nftables.conf
sudo nft -f /etc/nftables.conf
```

### 8.4 Test (from public-vm)

```
sudo apt install postgresql-client
psql -h 10.0.3.10 -U app_user -d app_db      # connects (asks for the password)
```

Running the same command on private-vm itself fails with "no pg_hba.conf entry", because the connection source would be 10.0.3.10, which is not allowed. On private-vm use `sudo -u postgres psql -d app_db` instead.

Docker NATs container traffic, so connections from containers on public-vm reach the database with the public VM's own address (10.0.1.10), which matches the `pg_hba` and firewall rules.

## 9. Docker on public-vm

1. Power off public-vm and raise its RAM to 2048 MB in VirtualBox, then start it again.
2. Install Docker and let your user run it:

```
sudo apt update
sudo apt install docker.io
sudo usermod -aG docker $USER
```

3. Log out and back in, then check `docker --version`.

## 10. The application and the Nginx reverse proxy

The application source is in [`app/`](../app/) (see its README for the endpoints).

### 10.1 Copy the code to public-vm

Make sure the folder contains no `venv` or `__pycache__`. Validate the Python files first, because copy/paste errors only show up at run time:

```
python3 -m py_compile app/main.py app/models.py app/schemas.py app/database.py
scp -J <user>@192.168.56.10 -r app <user>@10.0.1.10:~/lab-api
```

### 10.2 Build the image

On public-vm:

```
cd ~/lab-api
docker build -t lab-api:latest .
```

### 10.3 Database settings (kept on the VM only)

```
nano ~/lab-api.env
chmod 600 ~/lab-api.env
```

One line, no quotes (see `app/.env.example`):

```
DATABASE_URL=postgresql://app_user:<password>@10.0.3.10:5432/app_db
```

If the password has special characters (`@`, `:`, `/`) it must be URL-encoded; plain letters and digits avoid the problem.

### 10.4 Run the container

```
docker run -d --name lab-api --restart unless-stopped \
  --env-file ~/lab-api.env -p 127.0.0.1:8000:8000 lab-api:latest
docker logs lab-api
```

Expected in the logs: `Application startup complete`. The port is bound to `127.0.0.1`, so the service is reachable only through Nginx. If you fix the code and rebuild, remove the old container first (`docker rm -f lab-api`), otherwise the restart policy keeps restarting the old one.

### 10.5 Nginx reverse proxy

Use [`public-vm/etc/nginx/sites-available/lab-api`](../public-vm/etc/nginx/sites-available/lab-api), then:

```
sudo cp lab-api /etc/nginx/sites-available/lab-api
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/lab-api /etc/nginx/sites-enabled/lab-api
sudo nginx -t
sudo systemctl reload nginx
```

`nginx -t` must report `syntax is ok` and `test is successful` before the reload. The default site is removed because both sites would declare `default_server` on port 80.

### 10.6 Tests

From public-vm:

```
curl http://localhost/healthz
curl http://localhost/db-check
```

From the host (the full path: router DNAT, Nginx, container, firewall, database):

```
curl http://192.168.56.10/healthz
curl http://192.168.56.10/db-check
curl -X POST http://192.168.56.10/visits
curl http://192.168.56.10/visits
```

Also open `http://192.168.56.10/docs` in a browser. To confirm the data lives in the database and not in the container:

```
psql -h 10.0.3.10 -U app_user -d app_db -c "select * from visits;"
```

## 11. Intrusion detection with Suricata (router-vm)

Suricata runs on the router in IDS mode (alerts only). Design choices are explained in [`router-vm/README.md`](../router-vm/README.md).

### 11.1 Install and load the rules

```
free -h                       # the router has 2 GB; Suricata with the full ruleset needs a good part of it
sudo apt install suricata
suricata -V
sudo suricata-update          # downloads the Emerging Threats Open rules (about 53,000)
```

### 11.2 Configure

Keep a backup, then edit three places in `/etc/suricata/suricata.yaml` (excerpts in [`router-vm/etc/suricata/suricata.yaml.snippet`](../router-vm/etc/suricata/suricata.yaml.snippet)):

```
sudo cp /etc/suricata/suricata.yaml /etc/suricata/suricata.yaml.bak
```

1. `HOME_NET` (around line 18): comment out the default line and set `"[10.0.3.0/24]"`, the protected private subnet.
2. `af-packet` interface (around line 622): the default is `eth0`, which does not exist here. Set `enp0s8`.
3. `rule-files` (around line 2199): add `- /etc/suricata/rules/local.rules` under `- suricata.rules`, with the same indentation.

### 11.3 Add the local rule

```
sudo mkdir -p /etc/suricata/rules
sudo cp router-vm/etc/suricata/rules/local.rules /etc/suricata/rules/local.rules
```

The rule alerts when one source sends more than 20 TCP SYN packets within 10 seconds to the protected subnet. The threshold makes one scan produce one alert instead of thousands.

### 11.4 Validate and start

```
sudo suricata -T -v -c /etc/suricata/suricata.yaml
```

Always add `-v`: without it the "rules loaded" lines are hidden. Expected: `2 rule files processed` and no failed rules. If it still says `1 rule files processed`, the `rule-files` edit did not take effect.

```
sudo systemctl enable --now suricata
sudo tail -n 15 /var/log/suricata/suricata.log
```

Wait for `Engine started` (about 30 seconds, it loads the whole ruleset) before testing.

### 11.5 Test

On the router:

```
sudo tail -f /var/log/suricata/fast.log
```

On public-vm:

```
sudo nmap -Pn -sS -p 1-1000 10.0.3.10
```

Use `-Pn`: without it nmap reports "Host seems down", because the firewall drops its discovery probes. Expected alert on the router:

```
[1:1000001:1] LAB Possible TCP port scan [**] [Classification: Attempted Information Leak] [Priority: 2] {TCP} 10.0.1.10:38992 -> 10.0.3.10:25
```

The destination port is one the firewall blocks, which shows that Suricata sees the packets before nftables drops them. To check that packets are captured at all:

```
sudo grep capture.kernel_packets /var/log/suricata/stats.log | tail -3
```

The number must grow while traffic flows.

## 12. After a reboot

Reboot the router and repeat the host test (`curl -I http://192.168.56.10`) to confirm that the rules in `/etc/nftables.conf` and the forwarding setting persist, and that Suricata is running again (`systemctl is-active suricata`). Reboot public-vm and check that the container (restart policy) and Nginx come back by themselves:

```
docker ps
systemctl is-active nginx
curl http://192.168.56.10/healthz
```

## Next steps

Restricting the paths Nginx exposes, tightening the router's input chain, then automation. See the roadmap in the README.
