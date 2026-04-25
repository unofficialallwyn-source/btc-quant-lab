"use client";
import { useMemo, useState } from "react";
import { calculateUSSalary, USInput } from "@/lib/calculators/us";
import { formatCurrency } from "@/lib/utils";
import { BreakdownChart } from "./breakdown-chart";

const defaultInput: USInput = {
  gross: 95000,
  frequency: "annual",
  hoursPerWeek: 40,
  weeksPerYear: 52,
  filingStatus: "single",
  preTax401k: 5000,
  preTaxHealth: 2400,
  stateTaxRate: 5,
  bonus: 3000,
};

export function USCalculator() {
  const [input, setInput] = useState(defaultInput);
  const [view, setView] = useState<"annual" | "monthly">("annual");
  const result = useMemo(() => calculateUSSalary(input), [input]);
  const mult = view === "annual" ? 1 : 1 / 12;

  const setNum = (k: keyof USInput, v: string) => setInput((s) => ({ ...s, [k]: Math.max(0, Number(v) || 0) }));

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="card p-5 space-y-3">
        <h2 className="text-xl font-semibold">US Gross to Net Calculator</h2>
        <p className="helper">Estimates federal tax, FICA and optional state tax. Local taxes and credits may differ.</p>
        {["gross","hoursPerWeek","weeksPerYear","preTax401k","preTaxHealth","stateTaxRate","bonus"].map((k)=>(
          <label key={k} className="block"><span className="label">{k.replace(/([A-Z])/g," $1")}</span><input className="input" type="number" value={input[k as keyof USInput] as number} onChange={(e)=>setNum(k as keyof USInput,e.target.value)} /></label>
        ))}
        <div className="grid grid-cols-2 gap-3">
          <select className="input" value={input.frequency} onChange={(e)=>setInput(s=>({...s,frequency:e.target.value as USInput['frequency']}))}><option value="annual">Annual</option><option value="monthly">Monthly</option><option value="hourly">Hourly</option></select>
          <select className="input" value={input.filingStatus} onChange={(e)=>setInput(s=>({...s,filingStatus:e.target.value as USInput['filingStatus']}))}><option value="single">Single</option><option value="married_joint">Married joint</option><option value="head_household">Head household</option></select>
        </div>
      </div>
      <div className="space-y-4">
        <div className="card p-5">
          <div className="mb-3 flex items-center justify-between"><h3 className="font-semibold">Results</h3><div className="flex gap-2 text-xs"><button onClick={()=>setView("annual")} className="rounded border px-2 py-1">Annual</button><button onClick={()=>setView("monthly")} className="rounded border px-2 py-1">Monthly</button></div></div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="card p-3"><p className="helper">Gross</p><p className="font-semibold">{formatCurrency(result.grossAnnual*mult,"USD")}</p></div>
            <div className="card p-3"><p className="helper">Federal tax</p><p className="font-semibold">{formatCurrency(result.federalTax*mult,"USD")}</p></div>
            <div className="card p-3"><p className="helper">FICA</p><p className="font-semibold">{formatCurrency(result.ficaTax*mult,"USD")}</p></div>
            <div className="card p-3"><p className="helper">Net pay</p><p className="font-semibold text-green-600">{formatCurrency(result.netAnnual*mult,"USD")}</p></div>
          </div>
        </div>
        <div className="card p-5"><BreakdownChart data={[{name:"Net",value:result.netAnnual},{name:"Federal",value:result.federalTax},{name:"FICA",value:result.ficaTax},{name:"State",value:result.stateTax},{name:"Pre-tax",value:result.preTax}]} /></div>
      </div>
    </section>
  );
}
