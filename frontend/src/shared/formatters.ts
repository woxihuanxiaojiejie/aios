export function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatPercent(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return String(value);
  return `${Math.round(numeric * 10000) / 100}%`;
}

export function formatBoolean(value: boolean | null | undefined) {
  if (value === null || value === undefined) return "-";
  return value ? "是" : "否";
}

export function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.length ? value.join("、") : "-";
  if (typeof value === "boolean") return formatBoolean(value);
  return String(value);
}
