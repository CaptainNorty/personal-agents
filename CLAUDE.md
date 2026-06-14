# personal-agents

Monorepo with two independently-deployed pieces:

- **Backend** — FastAPI app in `app/` (Python, managed with `uv`). Runs on an
  EC2 instance as the `personal-agents` systemd service. Postgres DB.
- **Frontend** — `unknownUnknowns/`: the Unknown Unknowns PWA (Vite + React +
  TypeScript, Tailwind). Hosted on Firebase Hosting. Talks to the backend at
  `VITE_API_BASE_URL`.

> This is a **Vite/React** project, not Angular. The build command is
> `npm run build` (→ `tsc -b && vite build`, output in `dist/`). There is no
> `ng` anything.

---

# Deployment

There are two separate deploy paths with **different triggers**. Read this
before shipping:

| Piece    | Trigger                          | Automatic? |
| -------- | -------------------------------- | ---------- |
| Backend  | `git push origin main`           | ✅ Yes     |
| Frontend | manual `firebase deploy`         | ❌ No      |

> ⚠️ **The big gotcha:** pushing to `main` deploys the **backend only**. The
> frontend does **not** auto-deploy — you must build + `firebase deploy` by
> hand. So if a change touches both (e.g. a backend API change the UI relies
> on), pushing alone ships half of it.

## Backend — push to deploy

The backend deploys automatically via GitHub Actions on any push to `main`.

`.github/workflows/deploy.yml` SSHes into the EC2 box and runs:

```bash
cd ~/personal-agents
git pull origin main
~/.local/bin/uv sync          # install/update deps
sudo systemctl restart personal-agents
```

So to deploy the backend:

```bash
git push origin main
```

Then watch the run finish:

```bash
gh run watch          # or: gh run list --workflow=deploy.yml
```

If something looks wrong, SSH in and check the service:

```bash
sudo systemctl status personal-agents
sudo journalctl -u personal-agents -n 100 --no-pager
```

- Service name: `personal-agents`
- App lives in `~/personal-agents` on the box, deps via `uv`.
- Public URL: `https://norty-agents.duckdns.org` (API base
  `…/api/v1/uu`, set in `unknownUnknowns/.env.production`).

## Frontend — build + firebase deploy (manual)

All commands run from `unknownUnknowns/`.

### Step 0 (CRITICAL): use the PERSONAL Firebase account

There are **two** Google accounts in play and it's easy to deploy with the
wrong one:

- ✅ Personal — `adamloyd.norton@gmail.com` → owns the `unknownunknowns-38737`
  project. **Use this.**
- ❌ Work — `adam@somethingblueplanning.co` (Sixpence / Something Blue
  Planning). NOT this one.

Check who's active and switch before deploying:

```bash
firebase login:list
# If the personal account isn't listed yet, add it once:
firebase login:add adamloyd.norton@gmail.com
# Make it the active account:
firebase login:use adamloyd.norton@gmail.com
```

The project itself is already pinned to `unknownunknowns-38737` in
`.firebaserc`, so the only variable is **which account** is active. To be
extra safe, pass the account explicitly on deploy (see below).

### Step 1: build

```bash
npm install        # first time / after dependency changes
npm run build      # tsc -b && vite build → dist/
```

This uses `.env.production` (`VITE_API_BASE_URL` → the deployed backend).

### Step 2: deploy

```bash
firebase deploy --only hosting --account adamloyd.norton@gmail.com
```

- `--account` forces the right identity regardless of what's currently active —
  belt and suspenders against the Sixpence-account mistake.
- Output is served from `dist/` (see `firebase.json`), SPA-rewritten to
  `index.html`.
- Live site: the `unknownunknowns-38737` Firebase Hosting URL.

## Full-stack release checklist

When a change spans both backend and frontend:

1. `git push origin main` → backend auto-deploys; `gh run watch` until green.
2. `cd unknownUnknowns && npm run build`
3. `firebase deploy --only hosting --account adamloyd.norton@gmail.com`
4. Hard-refresh the site (the PWA service worker caches aggressively;
   `index.html` is `no-cache` but assets are immutable/hashed).

## Local development

- Backend: `docker-compose up` (Postgres + app on `:8000`).
- Frontend: `cd unknownUnknowns && npm run dev` (Vite dev server on `:5173`;
  proxies `/api/*` → `127.0.0.1:8000` per `vite.config.ts`).
