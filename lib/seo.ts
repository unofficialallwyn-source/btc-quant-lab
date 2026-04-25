import type { Metadata } from "next";

export const site = {
  name: "CompTrail",
  url: "https://example.com",
  description:
    "Understand CTC vs gross vs net salary with premium calculators for India and US payroll scenarios.",
};

export const defaultMetadata: Metadata = {
  metadataBase: new URL(site.url),
  title: { default: `${site.name} | Salary Clarity`, template: `%s | ${site.name}` },
  description: site.description,
  openGraph: {
    title: site.name,
    description: site.description,
    url: site.url,
    siteName: site.name,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: site.name,
    description: site.description,
  },
  alternates: { canonical: site.url },
};
