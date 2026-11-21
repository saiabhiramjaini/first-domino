# Deploy

| Part | Where | Address |
| --- | --- | --- |
| Web app | Vercel (deploys itself from GitHub) | `https://first-domino.abhiramtech.in` |
| API | One EC2 server: one Docker container, nginx + certbot for HTTPS | `https://api-first-domino.abhiramtech.in` |
| Database | Neon Postgres | private |
| Server image | Docker Hub `saiabhiramjaini/api-first-domino` | public |
| Demo customer agent | Not deployed: runs on the customer's own machine (your laptop) | talks to the API |

## Settings: code vs secrets

Non-secret settings are committed; only secrets live in Vercel and GitHub.

| | Committed (change by pushing) | Secret |
| --- | --- | --- |
| Web | `client/.env.production` | Vercel: `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `API_JWT_SECRET` |
| Server | `server/deploy/config.env` | GitHub `SERVER_ENV`: see `server/deploy/.env.example` |

## How a change ships

- **Server:** push to `main` touching `server/**` runs `.github/workflows/server.yml`: `check` (lint, types, tests) → `publish` (build the image, push `:<sha>` and `:latest`) → `deploy` (write `~/first-domino/.env` from `config.env` + `SERVER_ENV`, run `deploy/run-api.sh` over SSH to replace the `first-domino-api` container, then call `/health` over HTTPS). Pull requests run `check` only.
- **Web:** Vercel builds every push that touches `client/` (`client/vercel.json`). Pull requests get preview links.

## One-time setup

1. **Neon.** Create a project. Copy the **direct** connection string (not the `-pooler` one) and turn it into `postgresql+asyncpg://USER:PASSWORD@HOST/neondb?ssl=require` (drop `sslmode` and `channel_binding`). The API creates the tables on its first start.
2. **Docker Hub.** Create an access token (Account settings → Personal access tokens, Read & Write).
3. **EC2.** Ubuntu, `t2.medium` or similar, a fixed IP. Security group: 22 from your IP, 80 and 443 from anywhere. Run `server/deploy/bootstrap-ec2.sh` on it once (Docker, nginx, certbot), then set up nginx as in "nginx and HTTPS" below.
4. **DNS** for `abhiramtech.in`:
   - `api-first-domino` → `A` (DNS only, proxy off) → the Elastic IP
   - `first-domino` → `CNAME` → the value Vercel shows when you add the domain
5. **GitHub** (repository settings, or the `gh` commands below). Secrets are typed in by you, never pasted into chat.
   - Variables: `DOCKERHUB_USERNAME`, `EC2_HOST` (Elastic IP), `EC2_USER` (`ubuntu`)
   - Secrets: `DOCKERHUB_TOKEN`, `EC2_SSH_KEY` (the whole private key file), `SERVER_ENV` (a filled-in copy of `server/deploy/.env.example`)
6. **Vercel.** Import the GitHub repo with Root Directory `client`, add the domain, and add the four secrets above as Production environment variables.
7. **Google sign-in.** In the OAuth client, add origin `https://first-domino.abhiramtech.in` and redirect URI `https://first-domino.abhiramtech.in/api/auth/callback/google`.

```bash
gh variable set DOCKERHUB_USERNAME --body <docker-hub-user>
gh variable set EC2_HOST --body <elastic-ip>
gh variable set EC2_USER --body ubuntu
gh secret set DOCKERHUB_TOKEN
gh secret set EC2_SSH_KEY < ~/.ssh/<ec2-key>.pem
gh secret set SERVER_ENV < server/deploy/.env.production
```

`server/deploy/.env.production` is ignored by git; delete it after setting the secret.

## nginx and HTTPS

nginx runs on the server itself (not in Docker) and forwards to the API on `127.0.0.1:8000`.

```bash
sudo cp nginx.conf /etc/nginx/sites-available/api-first-domino
sudo ln -sf /etc/nginx/sites-available/api-first-domino /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api-first-domino.abhiramtech.in --redirect --agree-tos -m <your-email>
```

certbot adds the HTTPS part to the file and renews the certificate by itself.

## Acting as the customer

The demo agent is a separate thing: the "Equal AI (demo)" call assistant, a customer of First Domino. It is never deployed with the product. It runs on the customer's machine (your laptop) and talks to the live API, like any real customer.

1. Sign in once on `https://first-domino.abhiramtech.in` with Google.
2. Give your account the demo project and get its API key, on the server:
   ```bash
   sudo docker exec first-domino-api python -m fd_api.seed_demo --email <your-google-email>
   ```
3. On your laptop, in `server/`: copy `customer.env.example` to `.env.customer`, fill in `FIRST_DOMINO_API_KEY` and `OPENAI_API_KEY`.
4. Start the customer's replay worker, and leave it running:
   ```bash
   make customer-worker
   ```
5. In another terminal, record a failing call; it prints the link to watch the diagnosis:
   ```bash
   make customer-demo BUG=b02
   ```

## Useful on the server

```bash
sudo docker ps
sudo docker logs -f first-domino-api
```

Roll back: Actions → server → re-run the deploy job of an older green run (it redeploys that run's image tag).
