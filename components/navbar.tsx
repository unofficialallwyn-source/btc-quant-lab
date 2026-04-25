import Link from "next/link";
import { ThemeToggle } from "./theme-toggle";

export function Navbar() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/90 backdrop-blur">
      <nav className="container-page flex h-16 items-center justify-between">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          <span className="rounded-md bg-primary/15 px-2 py-1 text-primary">◢</span> CompTrail
        </Link>
        <div className="hidden gap-6 text-sm md:flex">
          <Link href="/india">India</Link>
          <Link href="/us">US</Link>
          <Link href="/guide/ctc-vs-gross-vs-net">Guide</Link>
          <Link href="/about">About</Link>
          <Link href="/contact">Contact</Link>
        </div>
        <ThemeToggle />
      </nav>
    </header>
  );
}
