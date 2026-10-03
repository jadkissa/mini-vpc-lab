# Mini-VPC Lab

A local, AWS-style cloud networking lab built on VirtualBox. It recreates the core ideas of an AWS VPC (public and private subnets, an internet gateway, NAT, route tables, security groups, a bastion host) using real virtual machines.

## Why this project

- Prepare for the AWS Solutions Architect Associate (SAA) by understanding networking and architecture from the inside, not only from diagrams.
- Practice Linux networking, firewalls, NAT, routing, and service isolation.
- Build a foundation for DevOps/DevSecOps work: automation, security monitoring, and reproducible environments.

## Architecture

```
                    Internet
                       |
              [ VirtualBox NAT ]
                       |
                +------+------+
                |  router VM  |   Internet Gateway + NAT Gateway
                |  10.0.1.1   |   + route tables + firewall
                |  10.0.3.1   |
                +---+-----+---+
          public-net  |     |  private-net
        10.0.1.0/24   |     |   10.0.3.0/24
                      |     |
              +-------+--+ +-+---------+
              |public-vm | |private-vm |
              |10.0.1.10 | |10.0.3.10  |
              | web app  | | database  |
              +----------+ +-----------+
```

- The router is the only path between the two subnets and the internet.
- The public subnet hosts the web application. Only selected inbound ports (80/443) are allowed through the router.
- The private subnet hosts the database. It can reach the internet outbound (updates, package installs) through NAT, but nothing outside can initiate a connection to it.
- Administration of the private VM goes through the public VM, which acts as a bastion host.

## Addressing plan

| Component | Interface | Address | Gateway |
|---|---|---|---|
| VPC (whole lab) | n/a | 10.0.0.0/16 | n/a |
| router | adapter 1 (NAT) | DHCP from VirtualBox | n/a |
| router | adapter 2 (public-net) | 10.0.1.1/24 | n/a |
| router | adapter 3 (private-net) | 10.0.3.1/24 | n/a |
| public-vm | public-net | 10.0.1.10/24 | 10.0.1.1 |
| private-vm | private-net | 10.0.3.10/24 | 10.0.3.1 |

Note: the private subnet uses 10.0.3.0/24 on purpose. VirtualBox's default NAT network uses 10.0.2.0/24, so using it for the lab would cause routing conflicts.

## AWS concept mapping

| AWS concept | In this lab |
|---|---|
| VPC | The 10.0.0.0/16 address space and its isolated internal networks |
| Public subnet | public-net (10.0.1.0/24) |
| Private subnet | private-net (10.0.3.0/24) |
| Internet Gateway | Router VM forwarding traffic to the NAT adapter |
| NAT Gateway | NAT (masquerade) rules on the router |
| Route tables | Routing configuration on each VM |
| Security groups | Firewall rules (nftables/ufw) per VM |
| EC2 instances | The three Debian VMs |
| Bastion host | public-vm used as the SSH jump host |
| GuardDuty / network monitoring (later) | Suricata IDS on the router |

## Environment

- Host: 16 GB RAM machine running VirtualBox
- Guest OS: Debian (netinst image), no desktop environment, SSH server and standard system utilities only

| VM | Role | RAM | CPU | Disk |
|---|---|---|---|---|
| router | Gateway, NAT, firewall, later IDS | 2048 MB | 2 | 15 GB |
| public-vm | Web application (Nginx) | 1024 MB | 1 | 10 GB |
| private-vm | Database (PostgreSQL) | 1024 MB | 1 | 10 GB |

### VirtualBox network settings

| VM | Adapter | Mode | Network name |
|---|---|---|---|
| router | 1 | NAT | n/a |
| router | 2 | Internal Network | `public-net` |
| router | 3 | Internal Network | `private-net` |
| router | 4 (planned) | Host-Only | for SSH from the host |
| public-vm | 1 | Internal Network | `public-net` |
| private-vm | 1 | Internal Network | `private-net` |

On the router's internal adapters (2 and 3), Promiscuous Mode is set to "Allow All" so the IDS can see traffic later.

Installation tip: the public and private VMs are installed only after the router is working, so they can reach the Debian mirrors through it. Otherwise they would need a temporary NAT adapter during install.

### Phase details and verification

**Phase 1: Router VM**
Create the VM with three adapters as above. Install Debian with only SSH server and standard system utilities.
Verify: the system boots, the NAT adapter gets an address, and `ip -br a` shows all interfaces.

**Phase 2: Router networking**
Assign static addresses to the two internal interfaces, enable IPv4 forwarding, add NAT masquerade on the NAT interface, set a default-deny forwarding policy with explicit allows.
Verify: the router has internet access and both internal interfaces are up with the planned addresses.

**Phase 3: Public VM**
Install Debian, set the static address and gateway, deploy a simple web application behind Nginx.
Verify: the VM reaches the internet via the router; the web app is reachable from the host through the router.

**Phase 4: Private VM**
Install Debian, set the static address and gateway, install PostgreSQL bound only to the private address.
Verify: the VM can run package updates (outbound NAT works) and is not reachable from outside.

**Phase 5: Access paths**
SSH to the private VM only through the public VM. Add a Host-Only adapter on the router for management from the host.
Verify: direct access to the private VM from outside fails; access through the bastion works.

**Phase 6: Security groups**
Public VM: allow 80/443 inbound, SSH only from the management path. Private VM: allow the database port only from the public VM, SSH only from the bastion. Router: forward only what is explicitly allowed.
Verify: each rule is tested both ways (allowed traffic passes, everything else is dropped).

**Phase 7: Application and database**
Connect the web app on the public VM to PostgreSQL on the private VM.
Verify: the app works end to end and the database is never exposed publicly.

**Phase 8: Intrusion detection**
Install Suricata on the router, monitor the internal interfaces, load the Emerging Threats ruleset. Start in IDS (alert-only) mode. Test with controlled scans (for example nmap from the public VM) and check the alerts. IPS (inline blocking) is a later, optional step once false positives are understood.
Verify: scans and test attacks generate alerts in the Suricata logs.

**Phase 9: Automation and docs**
Capture the setup as scripts or Vagrant/Ansible so the lab can be rebuilt quickly. Add diagrams and a troubleshooting section to this README.

**Phase 10: Move to AWS**
Rebuild the same topology on AWS (VPC, subnets, IGW, NAT Gateway, route tables, security groups, EC2, RDS) with Terraform, and compare it with the local version.

## AWS SAA topics this lab covers

- VPC design, CIDR planning, public vs private subnets
- Internet Gateway, NAT Gateway, route tables
- Security groups and the principle of least privilege
- Bastion host pattern and network isolation
- Multi-tier architecture (web tier, database tier)
- Monitoring and threat detection concepts (GuardDuty, VPC Traffic Mirroring, Network Firewall)

## Repository layout 

```
mini-vpc-lab/
  README.md
  docs/            diagrams, notes, troubleshooting
  router/          network and firewall configuration, IDS config
  public-vm/       web app and its configuration
  private-vm/      database configuration
  automation/      Vagrant / Ansible / scripts
```

## Notes and decisions

- Debian netinst is used for all VMs for consistency (one OS, one set of commands).
- LocalStack was considered, but it only emulates AWS APIs and does not teach real networking, so real VMs are used for this lab.
- The router starts with IDS-only monitoring to avoid blocking legitimate traffic while learning.