# CompTrail — CTC vs Gross vs Net Salary Platform

A production-ready Next.js (App Router) website focused on salary education and calculators for India and US users.

## Stack
- Next.js 15 + TypeScript
- Tailwind CSS
- next-themes (light/dark mode)
- Recharts for breakdown charts
- Lucide icons

## Features
- Premium-style home page with education + calculators
- India calculator: CTC, gross, tax, and in-hand estimates
- US calculator: gross-to-net with federal + FICA + optional state tax
- SEO routes: guide page + 5 article pages
- FAQ schema and article schema
- robots.txt and sitemap.xml
- About, Contact, Privacy Policy, Disclaimer pages
- AdSense-ready ad placeholders (easy to remove)
- Static-export friendly (`output: "export"`)

## Run locally
```bash
npm install
npm run dev
```

## Build
```bash
npm run build
```

## Deploy
Deploy the static output to Vercel, Netlify, Cloudflare Pages, or any static hosting that supports Next export output.

## Update tax constants
- India logic: `lib/calculators/india.ts`
- US logic: `lib/calculators/us.ts`

## Edit content
- Home + page copy: `app/page.tsx`
- Guide: `app/guide/ctc-vs-gross-vs-net/page.tsx`
- Articles: `app/articles/*/page.tsx`

## AdSense insertion points
- Generic slot component: `components/ad-placeholder.tsx`
- Current placements: home page sections in `app/page.tsx`

## Notes
Calculators are estimation tools for educational planning and not legal/tax advice.
