export type IndiaRegime = "old" | "new";

export interface IndiaInput {
  ctc: number;
  bonus: number;
  employerPf: number;
  gratuity: number;
  employerBenefits: number;
  employeePf: number;
  professionalTax: number;
  otherDeductions: number;
  oldRegimeDeductions: number;
  useStandardDeduction: boolean;
  regime: IndiaRegime;
}

const standardDeduction = 50000;

const slabs = {
  old: [
    { upto: 250000, rate: 0 },
    { upto: 500000, rate: 0.05 },
    { upto: 1000000, rate: 0.2 },
    { upto: Infinity, rate: 0.3 },
  ],
  new: [
    { upto: 300000, rate: 0 },
    { upto: 700000, rate: 0.05 },
    { upto: 1000000, rate: 0.1 },
    { upto: 1200000, rate: 0.15 },
    { upto: 1500000, rate: 0.2 },
    { upto: Infinity, rate: 0.3 },
  ],
};

const slabTax = (income: number, regime: IndiaRegime) => {
  let tax = 0;
  let prev = 0;
  for (const slab of slabs[regime]) {
    const taxable = Math.max(0, Math.min(income, slab.upto) - prev);
    tax += taxable * slab.rate;
    prev = slab.upto;
    if (income <= slab.upto) break;
  }
  return tax;
};

export const calculateIndiaSalary = (input: IndiaInput) => {
  const employerTotal = input.employerPf + input.gratuity + input.employerBenefits;
  const grossAnnual = Math.max(0, input.ctc - employerTotal);
  const grossTaxable = Math.max(0, grossAnnual + input.bonus);

  const totalDeductions =
    (input.useStandardDeduction ? standardDeduction : 0) +
    (input.regime === "old" ? input.oldRegimeDeductions : 0);

  const taxableIncome = Math.max(0, grossTaxable - totalDeductions - input.employeePf);
  const incomeTax = slabTax(taxableIncome, input.regime);
  const cess = incomeTax * 0.04;
  const totalTax = incomeTax + cess;
  const employeeDeductions = input.employeePf + input.professionalTax + input.otherDeductions;
  const netAnnual = Math.max(0, grossTaxable - totalTax - employeeDeductions);

  return {
    ctcAnnual: input.ctc,
    grossAnnual,
    netAnnual,
    grossMonthly: grossAnnual / 12,
    netMonthly: netAnnual / 12,
    taxAnnual: totalTax,
    employeeDeductionsAnnual: employeeDeductions,
    employerContributionsAnnual: employerTotal,
  };
};
