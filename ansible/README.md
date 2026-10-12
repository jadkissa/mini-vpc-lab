# Ansible automation

Ansible describes the **desired state** of each VM in files, so the lab can be configured again with one command instead of repeating manual steps. Ansible compares the current state with the desired one and changes only what is different.

Status: in progress. The baseline and the database tier are automated. The router and the web tier are next.

## What is automated, what stays manual

| Step | How |
|---|---|
| Create the VMs in VirtualBox, install Debian, set the static IP, enable SSH | Manual, once per VM (the bootstrap) |
| Packages, services and configuration of each VM | Ansible (`ansible-playbook site.yml`) |

```
Debian + IP + SSH   (manual, once)
        |
        v
ansible-playbook site.yml
   |- common     all VMs        base packages                         (done)
   |- private_vm private-vm     PostgreSQL: listening and pg_hba      (done, database and user creation next)
   |- router     router-vm      network, NAT, nftables, Suricata      (planned)
   '- public_vm  public-vm      Nginx, Docker, the application        (planned)
```

## Layout

```
ansible/
  ansible.cfg
  site.yml
  inventory/
    hosts.ini.example          copy to hosts.ini and fill in your username
  roles/
    common/tasks/main.yml
    private_vm/
      tasks/main.yml
      handlers/main.yml
```

## Requirements

- Ansible on the host machine (developed with Ansible core 2.16).
- SSH keys installed on all three VMs, because Ansible cannot type a password. Install them in order, router first (every other VM is reached through it), and check each one:

```
ssh-copy-id <user>@192.168.56.10
ssh-copy-id -o ProxyJump=<user>@192.168.56.10 <user>@10.0.1.10
ssh-copy-id -o ProxyJump=<user>@192.168.56.10,<user>@10.0.1.10 <user>@10.0.3.10

ssh <user>@192.168.56.10 hostname
ssh -J <user>@192.168.56.10 <user>@10.0.1.10 hostname
ssh -J <user>@192.168.56.10,<user>@10.0.1.10 <user>@10.0.3.10 hostname
```

- An inventory: `cp inventory/hosts.ini.example inventory/hosts.ini` and replace `<user>`. The real `hosts.ini` is ignored by git.
- The same `sudo` password on all VMs, or passwordless sudo, because `-K` asks for the password once.

## Run

Run everything from the `ansible/` folder (that is where `ansible.cfg` is found).

```
ansible all -m ping                          # can Ansible reach every VM?
ansible-playbook site.yml -K --check --diff  # dry run: shows what would change
ansible-playbook site.yml -K                 # apply
ansible-playbook site.yml -K                 # run again: expect changed=0 everywhere
```

`-K` asks for the sudo password once and uses it for all VMs.

## Roles

### common (all VMs)

| Task | Module | Desired state |
|---|---|---|
| Update the apt cache | `apt` | Cache not older than one hour |
| Ensure base packages | `apt` | `openssh-server`, `sudo`, `curl` present |

### private_vm (private-vm)

| Task | Module | Desired state |
|---|---|---|
| Install PostgreSQL | `apt` | `postgresql` present |
| Ensure the service runs | `service` | Started and enabled at boot |
| Listen on the private address | `lineinfile` | `listen_addresses = 'localhost,10.0.3.10'` in `postgresql.conf`; notifies the restart handler |
| Allow the application user | `lineinfile` | One `pg_hba.conf` rule for `app_db` / `app_user` from `10.0.1.10/32`; notifies the reload handler |

Handlers (`handlers/main.yml`) restart or reload PostgreSQL. They run only when the task that notified them really changed a file, and only once at the end of the play, so the service is not restarted on every run. A change of `listen_addresses` needs a restart; `pg_hba.conf` only needs a reload.

Not automated yet: creating `app_db` and `app_user` and setting the password. This is the next step, with Ansible Vault so the password is stored encrypted and never appears in the repository.

## Concepts used

- **Idempotency**: running the playbook twice gives `changed=0` the second time. `state: present` means "make sure it exists", not "install it again".
- **Check mode** (`--check --diff`): a dry run. The "Update the apt cache" task is always reported as changed in check mode, because Ansible cannot know whether the cache is fresh without running it.
- **`lineinfile`**: makes sure one line exists. The `regexp` decides which existing line counts as "the same line", so the line is replaced instead of duplicated on every run.
- **Handlers**: tasks that run only when notified by a task that changed something.

## Planned

- `private_vm`: database and user creation, with Ansible Vault for the password.
- `router` role: interfaces, forwarding, nftables, Suricata. The files already in `../router-vm/etc/` should be the single source of truth and be copied by the role instead of being repeated inside it.
- `public_vm` role: Nginx, Docker, the application container.
