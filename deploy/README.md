# Deploy

First Domino runs on one host with Docker Compose: Postgres, the API, the web app, the demo
customer's replay worker and Caddy. Caddy serves everything on one HTTPS name: `/v1/*` and
`/health` go to the API, the rest to the web app. The name is the host's public IP under
[sslip.io](https://sslip.io), so no DNS setup is needed and Let's Encrypt issues the certificate.

| File | What it is |
| --- | --- |
| `compose.prod.yml` | The five services. Only Caddy publishes ports (80 and 443) |
| `Caddyfile` | HTTPS and routing for `FD_DOMAIN` |
| `.env.example` | Every secret and setting the host needs. Copy to `deploy/.env` |
| `../backend/Dockerfile` | One image for the API (default command) and the worker |
| `../frontend/Dockerfile` | The web app image |

Secrets live only in `deploy/.env` on the host. It is ignored by git; never commit it.

## Try it on a laptop

```bash
cp deploy/.env.example deploy/.env   # keep FD_DOMAIN=localhost, fill in the rest
docker compose -f deploy/compose.prod.yml up --build
curl -k https://localhost/health      # {"ok":true}
```

Open `https://localhost` and accept Caddy's local certificate. Google sign-in works locally only
if the OAuth client also allows `https://localhost/api/auth/callback/google`.

## One EC2 instance

1. **Launch** an Ubuntu 24.04 instance, `t3.medium` (the web app build needs about 3 GB of
   memory) with a 30 GB disk. Security group: SSH (22) from your IP only; HTTP (80) and
   HTTPS (443) from anywhere.
2. **Give it a fixed IP**: allocate an Elastic IP and associate it with the instance. The
   public name is that IP under sslip.io, for example `3.110.20.5.sslip.io`.
3. **Install Docker and Git** over SSH:

   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker ubuntu && exit   # log in again so the group applies
   ```

4. **Get the code** and create the environment file:

   ```bash
   git clone <repository URL> first-domino && cd first-domino
   cp deploy/.env.example deploy/.env && chmod 600 deploy/.env
   ```

   Fill in `deploy/.env`: `FD_DOMAIN=<elastic IP>.sslip.io`, a random `POSTGRES_PASSWORD`,
   `API_JWT_SECRET` and `AUTH_SECRET` (each `openssl rand -hex 32`), the Google OAuth client,
   `OPENAI_API_KEY` and both model ids. Leave `FIRST_DOMINO_API_KEY` empty for now.
5. **Allow the sign-in redirect**: in the Google OAuth client, add the authorized redirect URI
   `https://<FD_DOMAIN>/api/auth/callback/google`.
6. **Start** Postgres, the API, the web app and Caddy:

   ```bash
   docker compose -f deploy/compose.prod.yml up -d --build
   curl https://<FD_DOMAIN>/health   # {"ok":true}
   ```

7. **Prepare the demo workspace** for the person who will sign in (a judge or you). This
   creates the "Equal AI (demo)" project for that Google email and prints the demo worker's
   API key:

   ```bash
   docker compose -f deploy/compose.prod.yml run --rm api \
     python -m fd_api.seed_demo --email person@example.com
   ```

   Put the printed key in `deploy/.env` as `FIRST_DOMINO_API_KEY`. When that person signs in
   with Google for the first time, they land in this project.
8. **Start the demo worker** (it is behind the `worker` profile so it never starts without a
   key):

   ```bash
   docker compose -f deploy/compose.prod.yml --profile worker up -d worker
   ```

## Day to day

| Task | Command (from the repository root) |
| --- | --- |
| Update to the latest code | `git pull && docker compose -f deploy/compose.prod.yml --profile worker up -d --build` |
| Follow the logs | `docker compose -f deploy/compose.prod.yml logs -f api worker` |
| Back up the database | `docker compose -f deploy/compose.prod.yml exec postgres pg_dump -U fd first_domino > backup.sql` |
| Stop everything | `docker compose -f deploy/compose.prod.yml --profile worker down` (add `-v` to delete the data) |

Tables are created when the API starts; there are no migrations during the hackathon. A schema
change on a deployed database means resetting it (`down -v`) or adding the column by hand.
