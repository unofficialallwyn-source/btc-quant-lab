"use client";
import { useState } from "react";

type Item = { q: string; a: string };

export function FaqAccordion({ items }: { items: Item[] }) {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={item.q} className="card p-4">
          <button className="w-full text-left font-medium" onClick={() => setOpen(open === i ? null : i)}>
            {item.q}
          </button>
          {open === i && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.a}</p>}
        </div>
      ))}
    </div>
  );
}
