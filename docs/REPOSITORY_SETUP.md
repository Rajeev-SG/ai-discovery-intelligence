# Repository bootstrap

Intended remote: `Rajeev-SG/ai-discovery-intelligence` (private).

From this scaffold directory on a machine with an authenticated GitHub CLI:

```bash
./scripts/publish_repo.sh
```

The script creates the private repository if it does not exist, pushes `main`, then creates the ordered implementation issues from `.github/issue-seeds/` without duplicating exact titles.

After bootstrap, a fresh coding agent needs only the prompt in `docs/AGENT_BOOTSTRAP.md`.
