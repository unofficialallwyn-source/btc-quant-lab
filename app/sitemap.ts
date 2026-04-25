import type { MetadataRoute } from "next";
const routes = ["","/india","/us","/guide/ctc-vs-gross-vs-net","/privacy-policy","/disclaimer","/about","/contact","/articles/in-hand-salary-india","/articles/ctc-vs-gross-vs-net-explained","/articles/gross-pay-vs-net-pay-us","/articles/taxes-and-take-home","/articles/compare-job-offers"];
export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({ url: `https://example.com${route}`, lastModified: new Date("2026-04-25") }));
}
