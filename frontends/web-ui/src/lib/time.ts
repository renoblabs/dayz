// Backend writes ISO timestamps in UTC but without a 'Z' suffix, so a naive
// `new Date(s)` interprets them as the browser's local time and shows up to
// a half-day skewed. This helper forces UTC parsing.
export function parseUtc(s: string): Date {
  if (!s) return new Date(NaN);
  // If the string already has a timezone designator, leave it alone.
  if (/[Z+-]\d?\d?(:\d\d)?$/.test(s)) return new Date(s);
  return new Date(s + 'Z');
}
