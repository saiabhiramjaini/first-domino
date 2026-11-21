# Deploy

| Part | Where | Address |
| --- | --- | --- |
| Web app | Vercel (deploys itself from GitHub) | `https://first-domino.abhiram.tech` |
| API + demo worker | One EC2 server, Docker Compose, Caddy for HTTPS | `https://api.first-domino.abhiram.tech` |
| Database | Neon Postgres | private |
| Server image | Docker Hub `<user>/first-domino-server` | public |

## How a change ships

- **Server:** push to `main` touching `server/**` runs `.github/workflows/server.yml`: `check` (lint, types, tests) → `publish` (build the image, push `:<sha>` and `:latest`) → `deploy` (copy `server/deploy/` files, write `.env` from `SERVER_ENV`, `docker compose pull && up`, then call `/health` over HTTPS). Pull requests run `check` only.
- **Web:** Vercel builds every push that touches `client/` (`client/vercel.json`). Pull requests get preview links.

## One-time setup

1. **Neon.** Create a project. Copy the **direct** connection string (not the `-pooler` one) and turn it into `postgresql+asyncpg://USER:PASSWORD@HOST/neondb?ssl=require` (drop `sslmode` and `channel_binding`). The API creates the tables on its first start.
2. **Docker Hub.** Create an access token (Account settings → Personal access tokens, Read & Write).
3. **EC2.** Ubuntu 24.04, `t3.small`, 20 GB disk, an Elastic IP. Security group: 22 from your IP, 80 and 443 from anywhere. Copy `server/deploy/bootstrap-ec2.sh` to it and run it once.
4. **DNS** for `abhiram.tech`:
   - `api.first-domino` → `A` → the Elastic IP
   - `first-domino` → `CNAME` → the value Vercel shows when you add the domain
5. **GitHub** (repository settings, or the `gh` commands below). Secrets are typed in by you, never pasted into chat.
   - Variables: `DOCKERHUB_USERNAME`, `EC2_HOST` (Elastic IP), `EC2_USER` (`ubuntu`), `API_DOMAIN` (`api.first-domino.abhiram.tech`)
   - Secrets: `DOCKERHUB_TOKEN`, `EC2_SSH_KEY` (the whole private key file), `SERVER_ENV` (the filled-in `server/deploy/.env.example`)
6. **Vercel.** Import the GitHub repo, set Root Directory to `client`, add the domain, and set these environment variables (Production):
   `NEXT_PUBLIC_APP_URL=https://first-domino.abhiram.tech`, `NEXT_PUBLIC_API_URL=https://api.first-domino.abhiram.tech`, `AUTH_URL=https://first-domino.abhiram.tech`, `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `API_JWT_SECRET` (same as `FD_API_WEB_JWT_SECRET`), `APP_ENV=prod`, `LOG_LEVEL=info`.
7. **Google sign-in.** In the OAuth client, add origin `https://first-domino.abhiram.tech` and redirect URI `https://first-domino.abhiram.tech/api/auth/callback/google`.

```bash
gh variable set DOCKERHUB_USERNAME --body <docker-hub-user>
gh variable set EC2_HOST --body <elastic-ip>
gh variable set EC2_USER --body ubuntu
gh variable set API_DOMAIN --body api.first-domino.abhiram.tech
gh secret set DOCKERHUB_TOKEN
gh secret set EC2_SSH_KEY < ~/.ssh/<ec2-key>.pem
gh secret set SERVER_ENV < server/deploy/.env.production
```

`server/deploy/.env.production` is ignored by git; delete it after setting the secret.

## Demo customer in production

After the first deploy and your first Google sign-in on the live site, on the server:

```bash
cd ~/first-domino && docker compose run --rm api python -m fd_api.seed_demo --email <your-google-email>
```

Put the printed key in `SERVER_ENV` as `FIRST_DOMINO_API_KEY`, set `COMPOSE_PROFILES=demo`, and re-run the workflow (Actions → server → Run workflow). The worker then starts. To record a failing call:

```bash
cd ~/first-domino && docker compose run --rm worker python -m fd_demo_agent.demo_live --bug b02
```

## Useful on the server

```bash
cd ~/first-domino && docker compose ps
cd ~/first-domino && docker compose logs -f api
```

Roll back: Actions → server → re-run the deploy job of an older green run (it redeploys that run's image tag).
