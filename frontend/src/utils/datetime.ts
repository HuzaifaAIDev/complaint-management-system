// The whole application displays date/time in Pakistan Standard Time
// (Asia/Karachi), regardless of what timezone the browser itself is set
// to. The backend already emits ISO-8601 timestamps with the Pakistan
// offset baked in, but `Date.prototype.toLocaleString()` still renders in
// the *browser's* local timezone unless a timeZone is explicitly passed -
// so every place in the UI that shows a date/time should go through these
// helpers instead of calling `new Date(...).toLocaleString()` directly.

const PK_TIME_ZONE = "Asia/Karachi";

export function formatPkDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-PK", {
    timeZone: PK_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPkDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-PK", {
    timeZone: PK_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatPkTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("en-PK", {
    timeZone: PK_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Current hour (0-23) in Pakistan Standard Time, regardless of the
 * visitor's device timezone - used for time-of-day greetings etc. */
export function getPkHour(): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: PK_TIME_ZONE,
    hour: "numeric",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const hourPart = parts.find((p) => p.type === "hour");
  return hourPart ? parseInt(hourPart.value, 10) : new Date().getHours();
}

/** Today's date in Pakistan Standard Time as a "YYYY-MM-DD" string,
 * suitable for the `min`/`value` of an <input type="date">. Computed from
 * the visitor's device clock but always expressed in PKT, so the "no past
 * dates" restriction on preferred date is based on Pakistan's calendar
 * date, not the browser's local one. */
export function todayPkDateInputValue(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: PK_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const y = parts.find((p) => p.type === "year")?.value ?? "1970";
  const m = parts.find((p) => p.type === "month")?.value ?? "01";
  const d = parts.find((p) => p.type === "day")?.value ?? "01";
  return `${y}-${m}-${d}`;
}
