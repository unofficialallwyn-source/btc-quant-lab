export type FilingStatus = "single" | "married_joint" | "head_household";
export type Frequency = "annual" | "monthly" | "hourly";

export interface USInput {
  gross: number;
  frequency: Frequency;
  hoursPerWeek: number;
  weeksPerYear: number;
  filingStatus: FilingStatus;
  preTax401k: number;
  preTaxHealth: number;
  stateTaxRate: number;
  bonus: number;
}

const standardDeduction: Record<FilingStatus, number> = {
  single: 14600,
  married_joint: 29200,
  head_household: 21900,
};

const brackets: Record<FilingStatus, { upto: number; rate: number }[]> = {
  single: [
    { upto: 11600, rate: 0.1 },
    { upto: 47150, rate: 0.12 },
    { upto: 100525, rate: 0.22 },
    { upto: 191950, rate: 0.24 },
    { upto: Infinity, rate: 0.32 },
  ],
  married_joint: [
    { upto: 23200, rate: 0.1 },
    { upto: 94300, rate: 0.12 },
    { upto: 201050, rate: 0.22 },
    { upto: 383900, rate: 0.24 },
    { upto: Infinity, rate: 0.32 },
  ],
  head_household: [
    { upto: 16550, rate: 0.1 },
    { upto: 63100, rate: 0.12 },
    { upto: 100500, rate: 0.22 },
    { upto: 191950, rate: 0.24 },
    { upto: Infinity, rate: 0.32 },
  ],
};

const progressiveTax = (income: number, status: FilingStatus) => {
  let tax = 0;
  let prev = 0;
  for (const slab of brackets[status]) {
    const taxable = Math.max(0, Math.min(income, slab.upto) - prev);
    tax += taxable * slab.rate;
    prev = slab.upto;
    if (income <= slab.upto) break;
  }
  return tax;
};

export const calculateUSSalary = (input: USInput) => {
  const annualBase =
    input.frequency === "annual"
      ? input.gross
      : input.frequency === "monthly"
        ? input.gross * 12
        : input.gross * input.hoursPerWeek * input.weeksPerYear;

  const grossAnnual = annualBase + input.bonus;
  const preTax = input.preTax401k + input.preTaxHealth;
  const taxableFederal = Math.max(0, grossAnnual - preTax - standardDeduction[input.filingStatus]);
  const federalTax = progressiveTax(taxableFederal, input.filingStatus);

  const socialSecurity = Math.min(grossAnnual, 168600) * 0.062;
  const medicare = grossAnnual * 0.0145;
  const ficaTax = socialSecurity + medicare;
  const stateTax = Math.max(0, grossAnnual - preTax) * (input.stateTaxRate / 100);

  const netAnnual = Math.max(0, grossAnnual - preTax - federalTax - ficaTax - stateTax);

  return {
    grossAnnual,
    grossMonthly: grossAnnual / 12,
    netAnnual,
    netMonthly: netAnnual / 12,
    federalTax,
    ficaTax,
    stateTax,
    preTax,
  };
};
