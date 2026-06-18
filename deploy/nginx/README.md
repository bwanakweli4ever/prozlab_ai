# Nginx configs for ProzLab production

## Profile upload 413 / fake CORS errors

If the browser shows CORS errors on `upload-profile-image` with **413 Request Entity Too Large**, nginx rejected the file before FastAPI. The 413 response has no CORS headers, so the browser reports CORS instead of the real error.

**Fix:** set `client_max_body_size` to at least `10M` on the API vhost.

```bash
sudo sed -i '/server_name api.prozlab.com;/a \    client_max_body_size 10M;' /etc/nginx/sites-available/api.prozlab.com
sudo nginx -t && sudo systemctl reload nginx
```

Or replace the site config:

```bash
sudo cp /var/www/prozlab_backend/deploy/nginx/api.prozlab.com.conf /etc/nginx/sites-available/api.prozlab.com
sudo ln -sf /etc/nginx/sites-available/api.prozlab.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

If certbot added SSL, merge `client_max_body_size 10M;` into the `listen 443 ssl` server block as well.
