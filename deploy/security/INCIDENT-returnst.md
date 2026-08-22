# Prozlab compromised — return.st redirect (Aug 2026)

## What happened

`https://prozlab.com` returns **nginx 307 → `https://return.st/`** (IP Stresser / Booter spam).

- **Not in GitHub / local repos** — app code is clean.
- **On the Vultr server** — nginx (or a malicious include) injects the redirect.
- **`api.prozlab.com` still answers** (API process may be OK).

Memory exhaustion is typical of malware (miners / flood helpers) running alongside the redirect.

## Immediate recovery (SSH as root)

```bash
ssh root@45.76.21.172

# 1) Confirm the poison
curl -sSIL https://prozlab.com | head -20
# Look for: Location: https://return.st/

grep -RIn 'return.st' /etc/nginx /var/www 2>/dev/null

# 2) Scan + fix
cd /var/www/prozlab_backend
git pull origin main
chmod +x deploy/security/cleanup-returnst-malware.sh
sudo bash deploy/security/cleanup-returnst-malware.sh        # scan first
sudo bash deploy/security/cleanup-returnst-malware.sh --fix # then fix

# 3) Rebuild clean frontend from git
cd /var/www/prozlab_dashboard
git fetch origin
git reset --hard origin/main
rm -rf .next node_modules
npm ci
npm run build
pm2 restart prozlab-dashboard

# 4) Backend
cd /var/www/prozlab_backend
git fetch origin
git reset --hard origin/main
pm2 restart all

# 5) Verify
curl -sSIL https://prozlab.com | head -20
# Must NOT redirect to return.st
```

## If nginx still redirects after --fix

Edit the live site by hand:

```bash
sudo nginx -T 2>/dev/null | less
# Search for return.st or "return 307"

sudo nano /etc/nginx/sites-enabled/prozlab.com
# Remove any line like:
#   return 307 https://return.st/;
#   rewrite ^ https://return.st/ permanent;

sudo nginx -t && sudo systemctl reload nginx
```

Also check:

- `/etc/nginx/nginx.conf` → `include` of unknown files
- `/etc/nginx/conf.d/*.conf`
- `/etc/nginx/modules-enabled/`
- Cloudflare page rules / Workers (if DNS is proxied)

## After the site loads again

1. Rotate **SSH keys**, DB password, `SECRET_KEY`, SMTP, Mailtrap, GitHub tokens.
2. `passwd` for root and deploy users.
3. Kill unknown high-memory processes (`htop`).
4. Remove unknown cron: `crontab -l`, `/etc/cron.d/`.
5. Enable Vultr firewall: only **22, 80, 443**.
6. Cloudflare: purge cache, enable Bot Fight / WAF if available.

## Do not

- Leave the site live while still redirecting (hurts SEO + visitors).
- Trust files modified in the last few days under `/var/www` without review.
- Reuse old server secrets after compromise.
