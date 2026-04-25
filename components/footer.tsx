import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border/70 py-10">
      <div className="container-page grid gap-4 text-sm text-slate-600 dark:text-slate-300 md:grid-cols-2">
        <p>© {new Date().getFullYear()} CompTrail. Salary education tools for informed career decisions.</p>
        <div className="flex flex-wrap justify-start gap-4 md:justify-end">
          <Link href="/privacy-policy">Privacy</Link>
          <Link href="/disclaimer">Disclaimer</Link>
          <Link href="/about">About</Link>
          <Link href="/contact">Contact</Link>
        </div>
      </div>
    </footer>
  );
}
