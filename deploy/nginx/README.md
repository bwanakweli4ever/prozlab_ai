# Nginx configs for ProzLab production

## Critical: HTTPS must use the correct certificate

If the browser shows `ERR_CERT_COMMON_NAME_INVALID` or CORS errors on `api.prozlab.com`, check the cert:

```bash
echo | openssl s_client -connect api.prozlab.com:443 -servername api.prozlab.com 2>/dev/null | openssl x509 -noout -subject
```

**Wrong:** `subject=CN=erp.bullnet.rw` or `CN=prozlab.com` only  
**Correct:** `CN=api.prozlab.com` (or SAN includes `api.prozlab.com`)

HTTP (`curl http://api.prozlab.com/...`) may work while HTTPS hits the wrong vhost (Bullnet ERP).

### One-command fix (on the server)

```bash
cd /var/www/prozlab_backend
git pull origin main
chmod +x deploy/nginx/fix-api-ssl.sh
sudo bash deploy/nginx/fix-api-ssl.sh
```

### Manual fix

```bash
# 1. See what catches api.prozlab.com on 443
sudo nginx -T 2>/dev/null | grep -B5 -A25 "server_name api.prozlab.com"

# 2. Install API config (proxies to :9000, 10MB uploads)
sudo cp /var/www/prozlab_backend/deploy/nginx/api.prozlab.com.conf /etc/nginx/sites-available/api.prozlab.com
sudo ln -sf /etc/nginx/sites-available/api.prozlab.com /etc/nginx/sites-enabled/

# 3. Disable conflicting HTTPS default (example — adjust path)
# sudo rm /etc/nginx/sites-enabled/erp.bullnet.rw

sudo nginx -t && sudo systemctl reload nginx

# 4. Issue cert for api.prozlab.com (outside Python venv)
deactivate 2>/dev/null || true
sudo certbot --nginx -d api.prozlab.com
```

## Profile upload 413 / fake CORS

Nginx default body limit is **1MB**. Set on **both** port 80 and 443 blocks:

```nginx
client_max_body_size 10M;
```

Without this, large uploads return **413** with no CORS headers → browser reports CORS.

## Verify after fix

```bash
curl -s https://api.prozlab.com/api/v1/auth/email/status
# Should return JSON from FastAPI, not Laravel HTML

pm2 restart prozlab-api --update-env
```
