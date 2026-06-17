# Personal deployment notes (local copy)

This folder is **tracked in git** as a starter kit. Your working copy lives in **`docs/personal/`**, which is **gitignored** so you can add hostnames, IPs, passwords references, and one-off commands without committing them.

## One-time setup

```bash
cp -r docs/personal-templates docs/personal
# Edit files under docs/personal/ with your domain, AWS account notes, etc.
```

## What's inside

| File | Purpose |
|------|---------|
| [`ENV.md`](ENV.md) | Every environment variable this app reads — local vs production |
| [`DEPLOYMENT_PLAYBOOK.md`](DEPLOYMENT_PLAYBOOK.md) | How Django apps usually go to production (generic + this project) |
| [`AWS_CHECKLIST.md`](AWS_CHECKLIST.md) | Your step-by-step AWS path with blanks to fill in |
| [`CONTAINERS.md`](CONTAINERS.md) | Docker / compose / future ECS notes for similar apps |

## Tracked vs personal

| Location | Git | Use for |
|----------|-----|---------|
| `docs/operations/DEPLOYMENT_AWS.md` | Tracked | Team runbook: EC2 + Caddy + gunicorn commands |
| `docs/personal/` | **Ignored** | Your domains, ARNs, SSH keys, deploy diary |
| `.env` | **Ignored** | Secrets on laptop or server |

After copying, open `docs/personal/AWS_CHECKLIST.md` and fill in the bracketed placeholders.
