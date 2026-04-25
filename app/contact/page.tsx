import type { Metadata } from "next";

export const metadata: Metadata = { title: "Contact", description: "Contact CompTrail for feedback and partnerships.", alternates: { canonical: "/contact" } };

export default function ContactPage() {
  return (
    <div className="container-page section">
      <h1 className="text-3xl font-bold">Contact</h1>
      <form className="mt-6 card max-w-xl p-6 space-y-3" aria-label="Contact form">
        <label className="block"><span className="label">Name</span><input className="input" required /></label>
        <label className="block"><span className="label">Email</span><input className="input" type="email" required /></label>
        <label className="block"><span className="label">Message</span><textarea className="input min-h-32" required /></label>
        <button className="rounded-xl bg-primary px-4 py-2 text-white">Send (UI only)</button>
      </form>
    </div>
  );
}
