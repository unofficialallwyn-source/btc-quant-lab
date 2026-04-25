import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "CTC vs Gross vs Net Salary: Complete Guide",
  description: "A practical guide to salary structure, deductions, and take-home pay for India and US professionals.",
  alternates: { canonical: "/guide/ctc-vs-gross-vs-net" },
};

export default function GuidePage() {
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "CTC vs Gross vs Net Salary",
    description: "Understand salary terms, formulas, and practical examples.",
    author: { "@type": "Organization", name: "CompTrail" },
  };
  return (
    <article className="container-page section prose prose-slate dark:prose-invert max-w-4xl">
      <h1>CTC vs Gross vs Net Salary: the complete practical guide</h1>
      <p>CTC is the employer cost, gross is earnings before employee deductions, and net is what reaches your account.</p>
      <h2>Formula</h2>
      <p><strong>Gross = CTC − employer contributions.</strong> <strong>Net = Gross − taxes − employee deductions.</strong></p>
      <h2>Common mistakes</h2>
      <ul><li>Comparing offers only on CTC</li><li>Ignoring tax regime or filing status</li><li>Skipping benefits valuation</li></ul>
      <p>Next: <Link href="/india">India calculator</Link> and <Link href="/us">US calculator</Link>.</p>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }} />
    </article>
  );
}
