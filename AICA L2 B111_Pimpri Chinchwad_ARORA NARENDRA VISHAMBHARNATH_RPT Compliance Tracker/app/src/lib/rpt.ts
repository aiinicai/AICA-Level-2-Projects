import {
  key,
  type Dataset,
  type Transaction,
  type Approval,
  type Mode,
  type Company,
} from "./parse";
import {
  CHECKS,
  ORDINARY_COURSE,
  RULE15_PCT,
  RULE15_OFFICE_MONTHLY,
  MARKET_TOLERANCE,
  sebiThreshold,
} from "./rules";
import { rupees, percent, dateLabel } from "./format";
export interface Exception {
  code: string;
  name: string;
  party: string;
  nature: string;
  amount: number;
  finding: string;
  law: string;
}
export interface Group {
  party: string;
  nature: string;
  relationship: string;
  total: number;
  vouchers: Transaction[];
}
export interface Market {
  party: string;
  item: string;
  nature: string;
  direction: string;
  rpRate: number | null;
  marketRate: number | null;
  deviation: number | null;
  result: "Flagged" | "Within tolerance" | "No comparable" | "Not tested";
  amount: number;
  total: number;
  quantity: number;
}
export interface Disclosure {
  category: string;
  party: string;
  nature: string;
  amount: number;
  balance: number;
  balanceNature: string;
}
export interface Aoc {
  part: string;
  party: string;
  relationship: string;
  nature: string;
  item: string;
  duration: string;
  value: number;
  board: string;
  shareholders: string;
}
export interface Results {
  mode: Mode;
  total: number;
  partyCount: number;
  exceptionPartyCount: number;
  rpts: Transaction[];
  groups: Group[];
  exceptions: Exception[];
  market: Market[];
  indAs: Disclosure[];
  aoc: Aoc[];
  threshold: number;
  addedParties: string[];
}
const sum = (t: Transaction[]) => t.reduce((s, v) => s + v.amount, 0);
const same = (a: string, b: string) => key(a) === key(b);
const inPeriod = (d: string, from: string, to: string) =>
  new Date(d).getTime() >= new Date(from).getTime() &&
  new Date(d).getTime() <= new Date(to).getTime();
export function covers(a: Approval, t: Transaction, body: string, anyNature = false) {
  return (
    same(a.party, t.party) &&
    a.body === body &&
    (anyNature || same(a.nature, t.nature)) &&
    a.date <= t.date &&
    inPeriod(t.date, a.from, a.to)
  );
}
export function rule15Limit(c: Company, nature: string) {
  return nature === "Office or place of profit"
    ? RULE15_OFFICE_MONTHLY
    : ["Sale of property", "Purchase of property"].includes(nature)
      ? c.netWorth * RULE15_PCT
      : c.turnover * RULE15_PCT;
}
export function crossesRule15(c: Company, g: Group) {
  const limit = rule15Limit(c, g.nature);
  return g.nature === "Office or place of profit"
    ? Math.max(...g.vouchers.map((t) => t.amount)) > limit
    : g.total >= limit;
}
export function calculate(data: Dataset, mode: Mode): Results {
  const { company: c, parties, approvals } = data;
  const full = new Set(parties.map((p) => key(p.party)));
  const scoped = parties.filter((p) => mode === "Listed" || key(p.recognised) !== "sebi only");
  const scope = new Set(scoped.map((p) => key(p.party)));
  const fy = data.transactions.filter((t) => inPeriod(t.date, c.start, c.end));
  const rpts = fy
    .filter((t) => scope.has(key(t.party)))
    .map((t) => ({ ...t, party: parties.find((p) => same(p.party, t.party))?.party ?? t.party }));
  const grouped = new Map<string, Transaction[]>();
  for (const t of rpts) {
    const k = JSON.stringify([key(t.party), key(t.nature)]);
    grouped.set(k, [...(grouped.get(k) ?? []), t]);
  }
  const groups: Group[] = Array.from(grouped.values())
    .flatMap((v) => {
      const first = v[0];
      if (!first) return [];
      return [
        {
          party: first.party,
          nature: first.nature,
          relationship: parties.find((p) => same(p.party, first.party))?.relationship ?? "",
          total: sum(v),
          vouchers: v,
        },
      ];
    })
    .sort((a, b) => a.party.localeCompare(b.party) || a.nature.localeCompare(b.nature));
  const market: Market[] = [];
  const itemGroups = new Map<string, Transaction[]>();
  for (const t of rpts) {
    const k = JSON.stringify([key(t.party), key(t.item), t.direction]);
    itemGroups.set(k, [...(itemGroups.get(k) ?? []), t]);
  }
  for (const v of itemGroups.values()) {
    const t = v[0];
    if (!t) continue;
    const comp = fy.filter(
      (x) => same(x.item, t.item) && x.direction === t.direction && !full.has(key(x.party)),
    );
    const qty = v.reduce((s, x) => s + x.quantity, 0);
    const cq = comp.reduce((s, x) => s + x.quantity, 0);
    const rpRate = qty > 0 ? sum(v) / qty : null;
    const marketRate = cq > 0 ? sum(comp) / cq : null;
    const deviation =
      rpRate !== null && marketRate !== null && marketRate !== 0 ? rpRate / marketRate - 1 : null;
    const flagged =
      deviation !== null &&
      (t.direction === "Cr" ? deviation > MARKET_TOLERANCE : deviation < -MARKET_TOLERANCE);
    market.push({
      party: t.party,
      item: t.item,
      nature: t.nature,
      direction: t.direction,
      rpRate,
      marketRate,
      deviation,
      result:
        comp.length === 0
          ? "No comparable"
          : deviation === null
            ? "Not tested"
            : flagged
              ? "Flagged"
              : "Within tolerance",
      amount:
        flagged && rpRate !== null && marketRate !== null
          ? Math.round(Math.abs(rpRate - marketRate) * qty)
          : 0,
      total: sum(v),
      quantity: qty,
    });
  }
  const exceptions: Exception[] = [];
  const add = (
    code: string,
    g: Pick<Group, "party" | "nature">,
    amount: number,
    finding: string,
    law: string,
  ) =>
    exceptions.push({
      code,
      name: CHECKS[code]?.name ?? code,
      party: g.party,
      nature: g.nature,
      amount,
      finding,
      law,
    });
  for (const g of groups) {
    const uncovered = g.vouchers.filter(
      (t) => !approvals.some((a) => covers(a, t, "Audit Committee")),
    );
    if (uncovered.length) {
      const dates = uncovered.map((t) => t.date).sort();
      const has = approvals.some((a) => same(a.party, g.party) && a.body === "Audit Committee");
      add(
        "C2",
        g,
        sum(uncovered),
        `${has ? "Audit committee approval had lapsed for these transactions" : "No audit committee approval on record"} (${uncovered.length} vouchers, ${dateLabel(dates[0] ?? "")} to ${dateLabel(dates[dates.length - 1] ?? "")})`,
        "Sec 177(4)(iv) Companies Act" + (mode === "Listed" ? "; Reg 23(2) SEBI LODR" : ""),
      );
    }
    const outside = !ORDINARY_COURSE.includes(g.nature);
    const flagged = market.some(
      (m) =>
        same(m.party, g.party) &&
        m.result === "Flagged" &&
        g.vouchers.some((t) => same(t.item, m.item) && t.direction === m.direction),
    );
    const applies = outside || flagged;
    if (applies && g.vouchers.some((t) => !approvals.some((a) => covers(a, t, "Board"))))
      add(
        "C5",
        g,
        g.total,
        `Section 188 applies (${outside ? "not in the ordinary course of business" : "not at arm's length (C4)"}); no board approval on record. If ratified within three months under Section 188(3), record the ratification.`,
        "Sec 188(1) Companies Act",
      );
    if (
      applies &&
      crossesRule15(c, g) &&
      g.vouchers.some((t) => !approvals.some((a) => covers(a, t, "Shareholders")))
    )
      add(
        "C6",
        g,
        g.total,
        `${g.nature === "Office or place of profit" ? "Monthly remuneration exceeds" : "Group total meets or exceeds"} ${rupees(rule15Limit(c, g.nature))} (${g.nature === "Office or place of profit" ? "monthly remuneration" : ["Sale of property", "Purchase of property"].includes(g.nature) ? "10% of net worth" : "10% of standalone turnover"}); no resolution on record. If ratified within three months under Section 188(3), record the ratification.`,
        "Sec 188(1), Rule 15(3)",
      );
  }
  for (const a of approvals.filter((a) => a.body === "Audit Committee")) {
    const used = sum(
      rpts.filter(
        (t) => same(t.party, a.party) && same(t.nature, a.nature) && inPeriod(t.date, a.from, a.to),
      ),
    );
    if (used > a.limit)
      add(
        "C3",
        a,
        used - a.limit,
        `Transactions of ${rupees(used)} against approved limit of ${rupees(a.limit)} (${a.id})`,
        "Sec 177(4)(iv), Rule 6A",
      );
  }
  for (const m of market.filter((m) => m.result === "Flagged"))
    add(
      "C4",
      m,
      m.amount,
      `${m.item}: average rate ${rupees(m.rpRate ?? 0)} vs ${rupees(m.marketRate ?? 0)} with unrelated parties (${percent(m.deviation ?? 0)}); estimated excess cost shown`,
      "Sec 188(1) arm's length test (screening at 10%)",
    );
  for (const a of approvals.filter((a) => a.body === "Board" && key(a.stayedOut) === "no")) {
    const v = rpts.filter((t) => same(t.party, a.party) && same(t.nature, a.nature));
    if (v.length)
      add(
        "C7",
        a,
        sum(v),
        `${a.interested} did not stay out of the board decision (${a.reference})`,
        "Sec 184(2) Companies Act",
      );
  }
  const threshold = sebiThreshold(c.consolidated);
  if (mode === "Listed")
    for (const p of scoped) {
      const v = rpts.filter((t) => same(t.party, p.party));
      const total = sum(v);
      if (
        total > threshold &&
        v.some((t) => !approvals.some((a) => covers(a, t, "Shareholders", true)))
      )
        add(
          "L2",
          {
            party: p.party,
            nature:
              new Set(v.map((t) => t.nature)).size === 1
                ? (v[0]?.nature ?? "All natures")
                : "All natures",
          },
          total,
          `Material transaction: ${rupees(total)} with this party exceeds ${rupees(threshold)} (${c.consolidated <= 200000000000 ? "10% of consolidated turnover" : "Schedule XII consolidated turnover threshold"}); no prior shareholder approval`,
          "Reg 23(4) and Schedule XII, SEBI LODR",
        );
    }
  exceptions.sort((a, b) => a.code.localeCompare(b.code) || a.party.localeCompare(b.party));
  const indAs = groups.flatMap((g) => {
    const p = parties.find((p) => same(p.party, g.party));
    return p && p.category !== "Not a related party under Ind AS 24"
      ? [
          {
            category: p.category,
            party: g.party,
            nature: g.nature,
            amount: g.total,
            balance: p.balance,
            balanceNature: p.balanceNature,
          },
        ]
      : [];
  });
  const earliest = (party: string, nature: string, body: string) =>
    approvals
      .filter((a) => same(a.party, party) && same(a.nature, nature) && a.body === body)
      .map((a) => a.date)
      .sort()[0];
  const duration = `${dateLabel(c.start)} to ${dateLabel(c.end)}`;
  const aoc: Aoc[] = market
    .filter((m) => m.result === "Flagged")
    .map((m) => ({
      part: "Part 1",
      party: m.party,
      relationship: parties.find((p) => same(p.party, m.party))?.relationship ?? "",
      nature: m.nature,
      item: m.item,
      duration,
      value: m.total,
      board: earliest(m.party, m.nature, "Board") ?? "Not obtained",
      shareholders: "Not applicable",
    }));
  for (const g of groups)
    if (
      key(parties.find((p) => same(p.party, g.party))?.recognised) !== "sebi only" &&
      !market.some(
        (m) => same(m.party, g.party) && m.nature === g.nature && m.result === "Flagged",
      ) &&
      crossesRule15(c, g)
    )
      aoc.push({
        part: "Part 2",
        party: g.party,
        relationship: g.relationship,
        nature: g.nature,
        item: "",
        duration,
        value: g.total,
        board:
          earliest(g.party, g.nature, "Board") ?? "Not applicable (ordinary course, arm's length)",
        shareholders: earliest(g.party, g.nature, "Shareholders") ?? "Not obtained",
      });
  return {
    mode,
    total: sum(rpts),
    partyCount: new Set(rpts.map((t) => key(t.party))).size,
    exceptionPartyCount: new Set(exceptions.map((e) => key(e.party))).size,
    rpts,
    groups,
    exceptions,
    market,
    indAs,
    aoc,
    threshold,
    addedParties: parties.filter((p) => key(p.recognised) === "sebi only").map((p) => p.party),
  };
}
