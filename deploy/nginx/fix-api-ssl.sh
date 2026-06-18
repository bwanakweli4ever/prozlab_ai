#!/bin/bash
# Fix api.prozlab.com nginx + SSL so HTTPS serves FastAPI (not Bullnet ERP).
set -euo pipefail

echo "=== Current api.prozlab.com nginx blocks ==="
sudo nginx -T 2>/dev/null | grep -n "server_name api.prozlab.com" || true

echo ""
echo "=== HTTPS certificate presented for api.prozlab.com ==="
echo | openssl s_client -connect api.prozlab.com:443 -servername api.prozlab.com 2>/dev/null \
  | openssl x509 -noout -subject 2>/dev/null || echo "Could not read cert"

echo ""
echo "=== Installing API nginx config ==="
sudo cp /var/www/prozlab_backend/deploy/nginx/api.prozlab.com.conf /etc/nginx/sites-available/api.prozlab.com
sudo ln -sf /etc/nginx/sites-available/api.prozlab.com /etc/nginx/sites-enabled/api.prozlab.com

echo ""
echo "=== Removing broken symlinks (if any) ==="
for f in /etc/nginx/sites-enabled/*; do
  if [ -L "$f" ] && [ ! -e "$f" ]; then
    echo "Removing broken link: $f"
    sudo rm -f "$f"
  fi
done

sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=== Requesting / renewing SSL for api.prozlab.com (snap certbot, outside venv) ==="
deactivate 2>/dev/null || true
sudo certbot --nginx -d api.prozlab.com --non-interactive --agree-tos --redirect || \
  sudo certbot --nginx -d api.prozlab.com

echo ""
echo "=== Verify ==="
curl -s "http://127.0.0.1:9000/api/v1/auth/email/status" | head -c 120 || true
echo ""
curl -sI "https://api.prozlab.com/api/v1/auth/email/status" | head -10
echo ""
echo | openssl s_client -connect api.prozlab.com:443 -servername api.prozlab.com 2>/dev/null \
  | openssl x509 -noout -subject 2>/dev/null

echo ""
echo "Done. Certificate subject must include api.prozlab.com"
