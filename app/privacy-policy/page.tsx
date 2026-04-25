import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy", description: "How CompTrail handles user privacy.", alternates: { canonical: "/privacy-policy" } };

export default function PrivacyPage() {
  return <div className="container-page section max-w-3xl"><h1 className="text-3xl font-bold">Privacy Policy</h1><p className="mt-4 text-sm text-slate-600 dark:text-slate-300">CompTrail does not require account signup and performs calculations in your browser. If analytics are enabled later, this page will be updated with controls and retention details.</p></div>;
}
