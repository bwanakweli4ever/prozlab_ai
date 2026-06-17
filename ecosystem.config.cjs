module.exports = {
  apps: [
    {
      name: "prozlab-api",
      cwd: "/var/www/prozlab_backend",
      script: "venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 9000",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      error_file: "logs/pm2-error.log",
      out_file: "logs/pm2-out.log",
      merge_logs: true,
      time: true,
    },
  ],
};
