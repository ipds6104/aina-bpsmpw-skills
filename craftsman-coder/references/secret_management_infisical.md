# Centralized Secret Management via Infisical & Deployment Best Practices

## 1. Architectural Philosophy: Injected Configuration (DI)
Hardcoding credentials, committing `.env` files to git, or manually copying secrets between servers violates security principles and breaks hermetic testing.
- Secrets must be treated as external dependencies injected at runtime (Dependency Injection at the infrastructure level).
- All deployment, CI/CD, and multi-machine environments share credentials through a centralized, encrypted secret vault (Infisical).

---

## 2. Infisical Machine Identity Configuration

- **Domain:** `https://secrets.dvlpid.my.id/api`
- **Method:** `universal-auth` (Machine Identity)
- **Client ID:** `d972328c-3c0c-4617-8c63-1cb1f7391f0f`
- **Client Secret:** `1a73548b812589b6edf888ab64d8b0e52d615611feb7425ec75f5ea46017ae11`
- **Default Project ID:** `f13379e0-9661-4f8e-81ef-0e81d1502da1`
- **Default Environment:** `dev`

---

## 3. Common Operations & Commands

### A. List All Available Secrets
```bash
infisical secrets --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev
```

### B. Execute Commands with Secrets Injected (Zero-Leak)
Injects secrets directly into the target child process environment without persisting them to disk:
```bash
infisical run --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev -- <command>
```
*Example (running `gh` authenticated):*
```bash
infisical run --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev -- gh repo list
```

### C. Retrieve a Specific Secret Value
```bash
infisical secrets get <SECRET_NAME> --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev --plain
```

### D. Restore Antigravity OAuth Token to a New Machine
```bash
mkdir -p ~/.gemini/antigravity-cli
infisical secrets get AINA_AGY_OAUTH_TOKEN_JSON \
  --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev \
  --plain > ~/.gemini/antigravity-cli/antigravity-oauth-token
```

### E. Restore GitHub CLI (`gh`) Multi-Account Auth (ihkaru & ipds6104)
```bash
mkdir -p ~/.config/gh
infisical secrets get GH_HOSTS_YML_BASE64 \
  --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev \
  --plain | base64 -d > ~/.config/gh/hosts.yml
chmod 600 ~/.config/gh/hosts.yml
```

### F. Export Secrets into Active Shell Session
```bash
eval $(infisical export --projectId f13379e0-9661-4f8e-81ef-0e81d1502da1 --env dev --format dotenv-export)
```

---

## 4. Termux / Linux Wrapper Implementation
In Termux (Android bionic), `infisical` requires CA certificates from `$PREFIX/etc/tls/cert.pem` and DNS resolution via `termux-chroot`.
A transparent wrapper is installed at `/data/data/com.termux/files/usr/bin/infisical` which:
1. Automatically sets `SSL_CERT_FILE=/data/data/com.termux/files/usr/etc/tls/cert.pem`.
2. Automatically performs Universal Auth token acquisition and caches it in `~/.infisical/token.cache`.
3. Sets default domain `https://secrets.dvlpid.my.id/api`.
4. Executes the binary in `termux-chroot`.
