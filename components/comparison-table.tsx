export function ComparisonTable() {
  const rows = [
    ["Definition", "Total employer cost", "Salary before employee taxes", "Take-home after deductions"],
    ["Includes", "Base + bonus + employer PF/benefits", "Base pay + allowances + bonus", "Gross minus tax + employee deductions"],
    ["Useful for", "Offer comparison", "Payroll planning", "Monthly budgeting"],
    ["Appears on", "Offer letter", "Payslip summary", "Bank credit / payslip net"],
  ];
  return (
    <div className="overflow-x-auto card">
      <table className="w-full min-w-[680px] text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50 text-left">
            <th className="p-3">Component</th><th className="p-3">CTC</th><th className="p-3">Gross</th><th className="p-3">Net / In-hand</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r[0]} className="border-b border-border/60 last:border-0">
              {r.map((c) => <td key={c} className="p-3 align-top">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
