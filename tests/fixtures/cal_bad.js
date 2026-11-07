// Buggy cal copy for tests: every month has 30 days.
const NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];
module.exports = function cal(month, year) {
  if (month < 1 || month > 12 || year < 1752 || year > 9999) throw new Error("unsupported");
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const days = 30;
  // Day of week of the 1st (0 = Sunday), Sakamoto's method.
  const t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4];
  const y = month < 3 ? year - 1 : year;
  const start = (y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) + t[month - 1] + 1) % 7;
  const list = [];
  for (let d = 1; d <= days; d++) if (!(year === 1752 && month === 9 && d > 2 && d < 14)) list.push(d);
  const title = `${NAMES[month - 1]} ${year}`;
  const rows = [" ".repeat(Math.floor((20 - title.length) / 2)) + title, "Su Mo Tu We Th Fr Sa"];
  let row = Array(year === 1752 && month === 9 ? 2 : start).fill("  ");
  for (const d of list) {
    row.push(String(d).padStart(2));
    if (row.length === 7) { rows.push(row.join(" ")); row = []; }
  }
  if (row.length) rows.push(row.join(" "));
  return rows.join("\n");
};
