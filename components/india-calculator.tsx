"use client";
import { useMemo, useState } from "react";
import { calculateIndiaSalary, IndiaInput } from "@/lib/calculators/india";
import { formatCurrency } from "@/lib/utils";
import { BreakdownChart } from "./breakdown-chart";

const defaultInput: IndiaInput = {
  ctc: 1200000,
  bonus: 120000,
  employerPf: 43200,
  gratuity: 24000,
  employerBenefits: 18000,
  employeePf: 43200,
  professionalTax: 2400,
  otherDeductions: 12000,
  oldRegimeDeductions: 150000,
  useStandardDeduction: true,
  regime: "new",
};

export function IndiaCalculator() {
  const [input, setInput] = useState<IndiaInput>(defaultInput);
  const [view, setView] = useState<"annual" | "monthly">("annual");
  const result = useMemo(() => calculateIndiaSalary(input), [input]);
  const mult = view === "annual" ? 1 : 1 / 12;

  const setNum = (k: keyof IndiaInput, v: string) => setInput((s) => ({ ...s, [k]: Math.max(0, Number(v) || 0) }));

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="card p-5 space-y-3">
        <h2 className="text-xl font-semibold">India Salary Calculator</h2>
        <p className="helper">Estimate CTC, gross, and in-hand salary. Figures are indicative, not legal tax advice.</p>
        {["ctc","bonus","employerPf","gratuity","employerBenefits","employeePf","professionalTax","otherDeductions","oldRegimeDeductions"].map((k)=>(
          <label key={k} className="block">
            <span className="label">{k.replace(/([A-Z])/g, " $1")}</span>
            <input className="input" type="number" value={input[k as keyof IndiaInput] as number} onChange={(e)=>setNum(k as keyof IndiaInput, e.target.value)} />
          </label>
        ))}
        <div className="flex gap-3">
          <select className="input" value={input.regime} onChange={(e)=>setInput(s=>({...s,regime:e.target.value as IndiaInput['regime']}))}>
            <option value="old">Old regime</option><option value="new">New regime</option>
          </select>
          <button className="input text-left" onClick={()=>setInput(defaultInput)}>Try sample data</button>
        </div>
      </div>
      <div className="space-y-4">
        <div className="card p-5">
          <div className="mb-3 flex items-center justify-between"><h3 className="font-semibold">Results</h3>
            <div className="flex gap-2 text-xs"><button onClick={()=>setView("annual")} className="rounded border px-2 py-1">Annual</button><button onClick={()=>setView("monthly")} className="rounded border px-2 py-1">Monthly</button></div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="card p-3"><p className="helper">CTC</p><p className="font-semibold">{formatCurrency(result.ctcAnnual*mult,"INR")}</p></div>
            <div className="card p-3"><p className="helper">Gross</p><p className="font-semibold">{formatCurrency(result.grossAnnual*mult,"INR")}</p></div>
            <div className="card p-3"><p className="helper">Tax</p><p className="font-semibold">{formatCurrency(result.taxAnnual*mult,"INR")}</p></div>
            <div className="card p-3"><p className="helper">Net in-hand</p><p className="font-semibold text-green-600">{formatCurrency(result.netAnnual*mult,"INR")}</p></div>
          </div>
        </div>
        <div className="card p-5">
          <BreakdownChart data={[{name:"Net",value:result.netAnnual},{name:"Tax",value:result.taxAnnual},{name:"Employee deductions",value:result.employeeDeductionsAnnual},{name:"Employer contributions",value:result.employerContributionsAnnual}]} />
        </div>
      </div>
    </section>
  );
}
