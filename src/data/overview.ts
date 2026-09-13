import type { Overview, Site } from "@/lib/sirocco";
import overviewJson from "../../public/data/ui/overview.json";
import sitesJson from "../../public/data/sites.json";

export const OVERVIEW = overviewJson as Overview;
export const SITES = sitesJson as Site[];
