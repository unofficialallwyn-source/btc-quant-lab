import type { Metadata } from "next";
import { USCalculator } from "@/components/us-calculator";
import { FaqAccordion } from "@/components/faq-accordion";

export const metadata: Metadata = {
  title: "US Gross to Net Salary Calculator",
  description: "Estimate federal tax, FICA and state tax to convert gross salary into take-home pay.",
  alternates: { canonical: "/us" },
};

export default function USPage() {
  const faq = [
    { q: "What is gross pay?", a: "Gross pay is earnings before taxes and deductions." },
    { q: "What is FICA?", a: "FICA includes Social Security and Medicare payroll taxes." },
    { q: "Does this include all state/local taxes?", a: "No. State rules vary; use this as directional planning." },
  ];
  return (
    <div className="container-page section space-y-8">
      <h1 className="text-3xl font-bold">US Gross vs Net Pay Calculator</h1>
      <p className="text-slate-600 dark:text-slate-300">Convert annual, monthly, or hourly gross pay into estimated take-home pay.</p>
      <USCalculator />
      <FaqAccordion items={faq} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({"@context":"https://schema.org","@type":"FAQPage","mainEntity":faq.map((f)=>({"@type":"Question","name":f.q,"acceptedAnswer":{"@type":"Answer","text":f.a}})) }) }} />
    </div>
  );
}
