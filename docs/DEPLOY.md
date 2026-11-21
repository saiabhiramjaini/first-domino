# Deploy

| Part | Where | Address |
| --- | --- | --- |
| Web app | Vercel (deploys itself from GitHub) | `https://first-domino.abhiramtech.in` |
| API | One EC2 server: one Docker container, nginx + certbot for HTTPS | `https://api-first-domino.abhiramtech.in` |
| Database | Neon Postgres | private |
| Server image | Docker Hub `saiabhiramjaini/api-first-domino` | public |
| SDK | PyPI [`first-domino`](https://pypi.org/project/first-domino/) | public |
| Example customer agents | Not deployed: the separate `call-assistant` and `sdk-agents` projects on the customer's machine | talk to the API |

## Settings: code vs secrets

Non-secret settings are committed; only secrets live in Vercel and GitHub.

| | Committed (change by pushing) | Secret |
| --- | --- | --- |
| Web | `client/.env.production` | Vercel: `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `API_JWT_SECRET`, and for email alerts `SENDER_EMAIL` and `SENDER_PASS` (a Gmail app password; without them alerts are off) |
| Server | `server/deploy/config.env` | GitHub `SERVER_ENV`: see `server/deploy/.env.example` |

## How a change ships

- **Server:** push to `main` touching `server/**` runs `.github/workflows/server.yml`: `check` (lint, types, tests) → `publish` (build the image, push `:<sha>` and `:latest`) → `deploy` (write `~/first-domino/.env` from `config.env` + `SERVER_ENV`, run `deploy/run-api.sh` over SSH to replace the `first-domino-api` container, then call `/health` over HTTPS). Pull requests run `check` only.
- **Web:** Vercel builds every push to `main` (`client/vercel.json`). Pull requests get preview links.
- **Schema:** the API runs the Alembic migrations (`fd_database/migrations/`) when it starts, under a Postgres advisory lock, before it serves. There is no separate migration step. Use the **direct** Neon host: the lock spans several transactions on one session, which a transaction pooler breaks.
- **SDK:** pushing a `sdk-v*` tag runs `.github/workflows/sdk-release.yml`, which publishes to PyPI. See [`RELEASE.md`](./RELEASE.md).

## First deploy with migrations

The database was created by `create_all` before Alembic. On its first start the new API finds the tables with no `alembic_version`, stamps the baseline revision `0001`, then applies `0002` (the drift columns and the `calibrate` check phase; fast, no table rewrite). Before that deploy:

1. Create a Neon branch of production as a restore point.
2. Confirm production matches the baseline. Start the image production runs now (before this change) against an empty local database, so its `create_all` builds the reference schema (identical to revision `0001`). Then diff `pg_dump --schema-only --no-owner` of that database against production. `create_all` never added columns to existing tables, so a production table created before a column was added would be stamped wrongly: add any missing column by hand before deploying.
3. Deploy. Expect `database.stamped`, then `database.migrated from_revision=0001 to_revision=0002`, then `api.started`. A failure leaves the container down and `run-api.sh` reports it; rerunning is safe (every change in `0002` skips when already applied). The previous image still runs against the upgraded schema, so rolling back needs no database change.

## One-time setup

1. **Neon.** Create a project. Copy the **direct** connection string (not the `-pooler` one) and turn it into `postgresql+asyncpg://USER:PASSWORD@HOST/neondb?ssl=require` (drop `sslmode` and `channel_binding`). The API builds the schema with its migrations on its first start.
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

The example customer is the separate `call-assistant` project, outside this repository. It is never deployed with the product: it installs the SDK, records calls and runs its replay worker on its own machine, like any real customer.

1. Sign in on `https://first-domino.abhiramtech.in` and create an API key on the Settings page.
2. In `call-assistant/`: copy `.env.example` to `.env`, set `FIRST_DOMINO_API_KEY`, `FIRST_DOMINO_BASE_URL=https://api-first-domino.abhiramtech.in`, `CALL_ASSISTANT_WEB_URL=https://first-domino.abhiramtech.in` and `OPENAI_API_KEY`.
3. `make worker` (leave it running), then `make call BUG=b02` in another terminal. It prints the link to watch the diagnosis.

## Useful on the server

```bash
sudo docker ps
sudo docker logs -f first-domino-api
```

Roll back: Actions → server → re-run the deploy job of an older green run (it redeploys that run's image tag).
