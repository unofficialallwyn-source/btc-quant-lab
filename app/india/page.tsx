import type { Metadata } from "next";
import { IndiaCalculator } from "@/components/india-calculator";
import { FaqAccordion } from "@/components/faq-accordion";

export const metadata: Metadata = {
  title: "India Salary Calculator (CTC to In-hand)",
  description: "Calculate annual and monthly in-hand salary from CTC with old/new tax regime estimates.",
  alternates: { canonical: "/india" },
};

export default function IndiaPage() {
  const faq = [
    { q: "Does CTC include employer PF?", a: "Yes, most offer letters include employer PF inside CTC." },
    { q: "Should I pick old or new regime?", a: "It depends on deductions and taxable income; compare both." },
    { q: "Is gratuity part of in-hand?", a: "No, gratuity is a deferred benefit under eligibility conditions." },
  ];

  return (
    <div className="container-page section space-y-8">
      <h1 className="text-3xl font-bold">India CTC vs Gross vs Net Calculator</h1>
      <p className="text-slate-600 dark:text-slate-300">Model your salary under old and new regime with visible assumptions.</p>
      <IndiaCalculator />
      <FaqAccordion items={faq} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({"@context":"https://schema.org","@type":"FAQPage","mainEntity":faq.map((f)=>({"@type":"Question","name":f.q,"acceptedAnswer":{"@type":"Answer","text":f.a}})) }) }} />
    </div>
  );
}
