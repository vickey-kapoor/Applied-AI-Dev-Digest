# AI Research Command Center Dashboard

A Next.js dashboard for the AI Research WhatsApp Digest project.

## Features

- **Dashboard Home**: Today's digest overview with quick stats
- **Papers Browser**: Browse and filter all fetched research papers
- **Reports Viewer**: View and download PDF reports
- **Analytics**: Charts and trends showing research insights
- **Settings**: View configuration and workflow controls

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts (for analytics charts)
- Lucide React (icons)

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Deployment

### Vercel

1. Connect your GitHub repository to Vercel
2. Set the root directory to `dashboard/`
3. Deploy - Vercel auto-detects Next.js

The dashboard fetches data from GitHub raw content URLs in production, so it will always show the latest data after each workflow run.

## Data Sources

The dashboard reads from:
- `data/papers.json` - All fetched research papers
- `data/digests.json` - Daily digest history
- `data/config.json` - Configuration settings
- `reports/` - PDF report files

In production (Vercel), data is fetched from GitHub's raw content API with 5-minute revalidation.

## Pages

- `/` - Dashboard home with stats and top paper
- `/papers` - Browse all papers with filtering
- `/reports` - View PDF reports
- `/analytics` - Charts and trends
- `/settings` - Configuration view
