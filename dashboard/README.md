# Applied AI Dev Digest — Dashboard

A Next.js app for tuning the [Applied AI Dev Digest](../README.md) without touching code. Deployed on Vercel; state lives in Vercel KV (Upstash Redis).

## Pages

| Route | What it does |
|---|---|
| `/topics` | Toggle topics and edit their keywords |
| `/preview` | See the next digest as a Telegram mockup and re-send it |
| `/history` | Past digests, with thumbs up/down that reweight ranking |
| `/stats` | Per-topic counts and trends |
| `/settings` | Pause or resume delivery, view configuration |

## Stack

Next.js (App Router) · TypeScript · Tailwind CSS · Vitest

## Development

```bash
npm install
npm run dev      # dev server
npm run build    # production build
npm run lint     # ESLint
npm test         # Vitest
```

Env vars and deployment steps are in [docs/OPERATIONS.md](../docs/OPERATIONS.md).
