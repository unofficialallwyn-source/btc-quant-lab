import type { Metadata } from "next";
export const metadata: Metadata = { title: "Gross Pay vs Net Pay in the US", description: "Understand paycheck deductions and what reduces take-home pay in the US.", alternates: { canonical: "/articles/gross-pay-vs-net-pay-us" } };
export default function Page(){return <article className="container-page section max-w-3xl"><h1 className="text-3xl font-bold">Gross pay vs net pay in the US</h1><p className="mt-4">Federal tax, FICA and benefit elections determine final take-home income.</p></article>;}
