import type { Metadata } from "next";

export const metadata: Metadata = { title: "Disclaimer", description: "Calculator and tax disclaimer for CompTrail.", alternates: { canonical: "/disclaimer" } };

export default function DisclaimerPage() {
  return <div className="container-page section max-w-3xl"><h1 className="text-3xl font-bold">Disclaimer</h1><p className="mt-4 text-sm text-slate-600 dark:text-slate-300">All salary outputs are estimates for educational use. Tax rules change frequently and vary by jurisdiction. Verify with your payroll team or licensed advisor before making financial decisions.</p></div>;
}
