#!/usr/bin/env bash
# Runs on the EC2 server (the deploy workflow pipes it over SSH). Replaces the API container
# with IMAGE_REF and waits until it answers on 127.0.0.1:8000, where nginx forwards to.
set -euo pipefail
: "${IMAGE_REF:?IMAGE_REF is required}"
name=first-domino-api
sudo docker pull "$IMAGE_REF"
sudo docker rm -f "$name" >/dev/null 2>&1 || true
sudo docker run -d --name "$name" --restart unless-stopped \
  --env-file ~/first-domino/.env -p 127.0.0.1:8000:8000 "$IMAGE_REF"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
    echo "api is up: $IMAGE_REF"
    sudo docker image prune -af >/dev/null
    exit 0
  fi
  sleep 2
done
echo "api did not start; last logs:" >&2
sudo docker logs --tail 50 "$name" >&2
exit 1
