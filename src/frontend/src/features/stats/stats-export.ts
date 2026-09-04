import { AXIOS_INSTANCE } from "@/api/axios-instance";

export async function downloadStatsCsv(from?: string, to?: string): Promise<void> {
  const res = await AXIOS_INSTANCE.get("/stats/export", {
    params: { from: from || undefined, to: to || undefined },
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "stats.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export type DailyRow = { date: string; entries: number; exits: number; revenue: number };

export async function fetchDailyRows(from?: string, to?: string): Promise<DailyRow[]> {
  const res = await AXIOS_INSTANCE.get("/stats/export", {
    params: { from: from || undefined, to: to || undefined },
    responseType: "text",
  });
  const lines = String(res.data).trim().split("\n").slice(1); // drop header
  return lines.filter(Boolean).map((l) => {
    const [date, entries, exits, revenue] = l.split(",");
    return { date, entries: Number(entries), exits: Number(exits), revenue: Number(revenue) };
  });
}
