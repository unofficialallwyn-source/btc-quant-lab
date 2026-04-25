import Link from "next/link";
import { IndiaCalculator } from "@/components/india-calculator";
import { USCalculator } from "@/components/us-calculator";
import { ComparisonTable } from "@/components/comparison-table";
import { FaqAccordion } from "@/components/faq-accordion";
import { AdPlaceholder } from "@/components/ad-placeholder";

const faq = [
  { q: "Is CTC my in-hand salary?", a: "No. CTC includes employer-side costs that are never paid directly to you." },
  { q: "What is gross salary?", a: "Gross is pay before taxes and employee deductions." },
  { q: "Why is net salary lower?", a: "Income tax, social contributions, and payroll deductions reduce take-home pay." },
  { q: "Can I compare India and US offers directly?", a: "Only after normalizing taxes, benefits, currency and living costs." },
  { q: "How accurate is this calculator?", a: "It is estimate-based and meant for planning, not legal or tax filing." },
  { q: "Does bonus affect taxes?", a: "Yes. Bonus usually raises taxable income in both countries." },
  { q: "Does this include local taxes?", a: "US local taxes and India special surcharges may not be fully covered." },
  { q: "Can I share calculations?", a: "Use your browser URL and copy values to compare offers with others." },
];

export default function HomePage() {
  return (
    <>
      <section className="section bg-gradient-to-b from-primary/10 via-transparent to-transparent">
        <div className="container-page text-center">
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl">CTC vs Gross vs Net Salary, explained with precision.</h1>
          <p className="mx-auto mt-4 max-w-3xl text-slate-600 dark:text-slate-300">CompTrail helps professionals in India and the US decode payslips, estimate take-home pay, and compare job offers with confidence.</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href="#calculator" className="rounded-xl bg-primary px-5 py-3 text-white">Calculate Salary</Link>
            <Link href="/india" className="rounded-xl border px-5 py-3">Explore India Calculator</Link>
            <Link href="/us" className="rounded-xl border px-5 py-3">Explore US Calculator</Link>
          </div>
          <p className="mt-4 text-xs text-slate-500">Transparent assumptions. No signup. No backend. Estimate only.</p>
        </div>
      </section>

      <section id="calculator" className="section"><div className="container-page space-y-4"><h2 className="text-2xl font-semibold">Interactive Salary Calculators</h2><p className="text-slate-600 dark:text-slate-300">Switch between India and US flows to see live monthly and annual salary breakdowns.</p><div className="grid gap-10"><IndiaCalculator /><USCalculator /></div></div></section>

      <section className="section"><div className="container-page space-y-4"><h2 className="text-2xl font-semibold">CTC, Gross, and Net: quick difference</h2><ComparisonTable /></div></section>

      <section className="section"><div className="container-page grid gap-6 lg:grid-cols-2"><div className="card p-6"><h3 className="text-xl font-semibold">India example</h3><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">CTC ₹12,00,000 may become gross ₹11,14,800 and net monthly around ₹72,000 depending on regime and deductions.</p></div><div className="card p-6"><h3 className="text-xl font-semibold">US example</h3><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Gross $95,000 can lead to net monthly around $5,700 after federal tax, FICA and pre-tax benefits.</p></div></div></section>

      <section className="section"><div className="container-page space-y-4"><h2 className="text-2xl font-semibold">Frequently asked questions</h2><FaqAccordion items={faq} /></div></section>

      <section className="section"><div className="container-page grid gap-4 md:grid-cols-2"><div className="card p-6"><h3 className="font-semibold">Learn deeply</h3><p className="my-2 text-sm">Read the full guide and related salary education articles.</p><Link href="/guide/ctc-vs-gross-vs-net" className="text-primary">Open full guide →</Link></div><AdPlaceholder label="In-content ad slot" /></div></section>
    </>
  );
}
