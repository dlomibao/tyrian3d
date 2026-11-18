// pm2 app for the scores service. pm2 itself runs under nvm's Node 18 on the server, so the app
// runs the system Node 22 directly (interpreter "none"). Replace <user> before use.
module.exports = {
  apps: [
    {
      name: "tyrian-scores",
      cwd: "/home/<user>/apps/tyrian-scores/app",
      script: "/usr/bin/node",
      interpreter: "none",
      args: "--disable-warning=ExperimentalWarning --env-file=/home/<user>/apps/tyrian-scores/scores.env server.mjs",
      autorestart: true,
      max_restarts: 20,
      restart_delay: 2000,
      max_memory_restart: "256M",
      time: true,
      // System Node first (pm2 itself lives under nvm).
      env: { PATH: "/usr/bin:/bin:/usr/local/bin", NODE_ENV: "production" },
    },
  ],
};
