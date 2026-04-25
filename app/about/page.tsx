import type { Metadata } from "next";

export const metadata: Metadata = { title: "about", description: "CompTrail about page.", alternates: { canonical: "/about" } };

export default function Page() {
  return <div className="container-page section"><h1 className="text-3xl font-bold capitalize">about</h1><div className="mt-4 card p-6 text-sm text-slate-600 dark:text-slate-300">about content for AdSense readiness. Calculators are estimates only and not tax, payroll, or legal advice.</div></div>;
}
