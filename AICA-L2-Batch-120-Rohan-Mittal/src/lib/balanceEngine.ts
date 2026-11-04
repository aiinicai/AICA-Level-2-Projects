import { formatMoney } from "./currencies";

// Pure balance math. All amounts are integer minor units (cents, fils, yen).
export type Share = { memberId: string; cents: number };
export type Result = { ok: true; shares: Share[] } | { ok: false; error: string };
export type Transfer = { from: string; to: string; cents: number; currency?: string };

export const toCents = (n: number | string) => Math.round(Number(n) * 100);

function priorityOrder(ids: string[], payer?: string) {
  return payer && ids.includes(payer) ? [payer, ...ids.filter((i) => i !== payer)] : ids;
}

export function splitEqual(total: number, participants: string[], payer?: string): Result {
  if (!participants.length) return { ok: false, error: "Pick at least one person" };
  if (total <= 0) return { ok: false, error: "Amount must be positive" };
  const base = Math.floor(total / participants.length);
  let rem = total - base * participants.length;
  const extra = new Set<string>();
  for (const id of priorityOrder(participants, payer)) if (rem-- > 0) extra.add(id);
  return {
    ok: true,
    shares: participants.map((id) => ({ memberId: id, cents: base + (extra.has(id) ? 1 : 0) })),
  };
}

export function splitExact(total: number, shares: Share[]): Result {
  const sum = shares.reduce((s, x) => s + x.cents, 0);
  if (!shares.length) return { ok: false, error: "Pick at least one person" };
  if (shares.some((s) => s.cents < 0)) return { ok: false, error: "Amounts cannot be negative" };
  if (sum !== total) return { ok: false, error: `Remaining to allocate: ${(total - sum) / 100}` };
  return { ok: true, shares };
}

export function splitPercentage(
  total: number,
  pcts: { memberId: string; pct: number }[],
  payer?: string,
): Result {
  if (!pcts.length) return { ok: false, error: "Pick at least one person" };
  const sum = pcts.reduce((s, x) => s + x.pct, 0);
  if (Math.abs(sum - 100) > 0.001)
    return { ok: false, error: `Percentages total ${+sum.toFixed(2)}%, need 100%` };
  const shares = pcts.map((p) => ({
    memberId: p.memberId,
    cents: Math.round((total * p.pct) / 100),
  }));
  const delta = total - shares.reduce((s, x) => s + x.cents, 0);
  if (delta) {
    const target = priorityOrder(
      pcts.map((p) => p.memberId),
      payer,
    )[0];
    shares.find((s) => s.memberId === target)!.cents += delta;
  }
  return { ok: true, shares };
}

export type LedgerExpense = { paidBy: string; cents: number; shares: Share[]; currency?: string };
export type LedgerSettlement = { from: string; to: string; cents: number; currency?: string };

export function netBalances(
  memberIds: string[],
  expenses: LedgerExpense[],
  settlements: LedgerSettlement[],
) {
  const net: Record<string, number> = Object.fromEntries(memberIds.map((id) => [id, 0]));
  const add = (id: string, v: number) => (net[id] = (net[id] ?? 0) + v);
  for (const e of expenses) {
    add(e.paidBy, e.cents);
    for (const s of e.shares) add(s.memberId, -s.cents);
  }
  for (const s of settlements) {
    add(s.from, s.cents);
    add(s.to, -s.cents);
  }
  return net;
}

export function simplifyDebts(net: Record<string, number>, currency?: string): Transfer[] {
  const debtors = Object.entries(net)
    .filter(([, v]) => v < 0)
    .map(([id, v]) => ({ id, v: -v }));
  const creditors = Object.entries(net)
    .filter(([, v]) => v > 0)
    .map(([id, v]) => ({ id, v }));
  const out: Transfer[] = [];
  while (debtors.length && creditors.length) {
    debtors.sort((a, b) => b.v - a.v);
    creditors.sort((a, b) => b.v - a.v);
    const d = debtors[0]!,
      c = creditors[0]!;
    const amt = Math.min(d.v, c.v);
    out.push({ from: d.id, to: c.id, cents: amt, ...(currency ? { currency } : {}) });
    d.v -= amt;
    c.v -= amt;
    if (!d.v) debtors.shift();
    if (!c.v) creditors.shift();
  }
  return out;
}

/**
 * Calculates net balances grouped by currency without netting across currencies.
 */
export function netBalancesByCurrency(
  memberIds: string[],
  expenses: LedgerExpense[],
  settlements: LedgerSettlement[],
): Record<string, Record<string, number>> {
  const result: Record<string, Record<string, number>> = {};

  const ensureCurr = (curr: string) => {
    if (!result[curr]) {
      result[curr] = Object.fromEntries(memberIds.map((id) => [id, 0]));
    }
    return result[curr]!;
  };

  for (const e of expenses) {
    const curr = (e.currency || "AED").toUpperCase();
    const map = ensureCurr(curr);
    map[e.paidBy] = (map[e.paidBy] ?? 0) + e.cents;
    for (const s of e.shares) {
      map[s.memberId] = (map[s.memberId] ?? 0) - s.cents;
    }
  }

  for (const s of settlements) {
    const curr = (s.currency || "AED").toUpperCase();
    const map = ensureCurr(curr);
    map[s.from] = (map[s.from] ?? 0) + s.cents;
    map[s.to] = (map[s.to] ?? 0) - s.cents;
  }

  return result;
}

/**
 * Calculates pairwise balances between two users across all currencies.
 * A positive value means userB owes userA.
 * A negative value means userA owes userB.
 */
export function calculatePairwiseBalances(
  userA: string,
  userB: string,
  expenses: LedgerExpense[],
  settlements: LedgerSettlement[],
): Record<string, number> {
  const netByCurr: Record<string, number> = {};

  for (const e of expenses) {
    const curr = (e.currency || "AED").toUpperCase();
    const shareB = e.shares.find((s) => s.memberId === userB)?.cents ?? 0;
    const shareA = e.shares.find((s) => s.memberId === userA)?.cents ?? 0;

    if (e.paidBy === userA && shareB > 0) {
      // User A paid for User B -> B owes A
      netByCurr[curr] = (netByCurr[curr] ?? 0) + shareB;
    } else if (e.paidBy === userB && shareA > 0) {
      // User B paid for User A -> A owes B (so net for A decreases)
      netByCurr[curr] = (netByCurr[curr] ?? 0) - shareA;
    }
  }

  for (const s of settlements) {
    const curr = (s.currency || "AED").toUpperCase();
    if (s.from === userB && s.to === userA) {
      // User B paid User A -> reduces what B owes A
      netByCurr[curr] = (netByCurr[curr] ?? 0) - s.cents;
    } else if (s.from === userA && s.to === userB) {
      // User A paid User B -> increases what B owes A
      netByCurr[curr] = (netByCurr[curr] ?? 0) + s.cents;
    }
  }

  return netByCurr;
}

// -------------------------------------------------------------
// SCOPED FRIEND LEDGER & PLAIN-LANGUAGE EXPLANATION ENGINE
// -------------------------------------------------------------

export type ScopeBreakdownItem = {
  scopeId: "direct" | string; // "direct" or groupId
  scopeName: string; // "Direct" or group.name
  isDirect: boolean;
  netUnits: number; // > 0: friend owes user, < 0: user owes friend, 0: settled
  userOwesFriendUnits: number;
  friendOwesUserUnits: number;
};

export type CurrencyBalanceBreakdown = {
  currency: string;
  totalNetUnits: number; // > 0: friend owes user, < 0: user owes friend, 0: settled
  userOwesFriendUnits: number;
  friendOwesUserUnits: number;
  scopes: ScopeBreakdownItem[];
  explanation: string;
};

export type FriendLedgerTransaction = {
  id: string;
  type: "expense" | "settlement";
  scope: "direct" | "group";
  groupId?: string | null;
  groupName?: string | null;
  friendshipId?: string | null;
  date: string;
  description: string;
  category?: string | undefined;
  currency: string;
  amountUnits: number;
  paidByUid: string;
  paidByName?: string;
  netImpactForUser: number; // > 0: friend owes user, < 0: user owes friend
  userShareUnits: number;
  friendShareUnits: number;
  fromUid?: string;
  toUid?: string;
  note?: string | null;
  rawExpense?: DirectExpenseInput;
  rawSettlement?: unknown;
};

export type SharedGroupInput = {
  id: string;
  name: string;
  members: { id: string; user_id: string | null; name: string }[];
  expenses: {
    id: string;
    group_id?: string | null;
    participant_uids?: string[];
    description: string;
    category?: string | undefined;
    amount_units: number;
    currency: string;
    paid_by_uid: string;
    paid_by_member_id?: string | null;
    split_type?: string;
    expense_date: string;
    note?: string | null;
    created_by?: string | null;
    splits: {
      member_id?: string;
      user_id?: string | null;
      amount_units: number;
      percentage?: number | null;
    }[];
  }[];
  settlements: {
    id: string;
    group_id?: string | null;
    participant_uids?: string[];
    from_member_id?: string | null;
    to_member_id?: string | null;
    from_uid: string;
    to_uid: string;
    amount_units: number;
    currency: string;
    settled_on: string;
    note?: string | null;
  }[];
};

export type DirectExpenseInput = {
  id: string;
  friendship_id?: string | null;
  participant_uids?: string[];
  description: string;
  category?: string | undefined;
  amount_units: number;
  currency: string;
  paid_by_uid: string;
  paid_by_member_id?: string | null;
  split_type?: string;
  expense_date: string;
  note?: string | null;
  created_by?: string | null;
  splits: {
    member_id?: string;
    user_id?: string | null;
    amount_units: number;
    percentage?: number | null;
  }[];
};

export type DirectSettlementInput = {
  id: string;
  friendship_id?: string | null;
  participant_uids?: string[];
  from_uid: string;
  to_uid: string;
  amount_units: number;
  currency: string;
  settled_on: string;
  note?: string | null;
};

export function formatPlainBalanceExplanation(
  friendName: string,
  currency: string,
  scopes: ScopeBreakdownItem[],
  totalNet: number,
): string {
  const activeScopes = scopes.filter((s) => s.netUnits !== 0);
  if (activeScopes.length === 0) {
    return `All settled up in ${currency}`;
  }

  const posScopes = activeScopes.filter((s) => s.netUnits > 0);
  const negScopes = activeScopes.filter((s) => s.netUnits < 0);

  const formatScopeItem = (s: ScopeBreakdownItem, units: number) => {
    const formattedAmt = formatMoney(units, currency);
    return s.isDirect ? `${formattedAmt} directly` : `${formattedAmt} from ${s.scopeName}`;
  };

  if (totalNet > 0) {
    const posParts = posScopes.map((s) => formatScopeItem(s, s.netUnits));
    const totalFormatted = formatMoney(totalNet, currency);
    if (negScopes.length === 0) {
      return `${friendName} owes you ${totalFormatted}: ${posParts.join(" + ")}`;
    }
    const negSum = negScopes.reduce((acc, s) => acc + Math.abs(s.netUnits), 0);
    const negParts = negScopes.map((s) => formatScopeItem(s, Math.abs(s.netUnits)));
    return `${friendName} owes you ${totalFormatted}: ${posParts.join(" + ")} · offset by ${formatMoney(negSum, currency)} you owe from ${negParts.join(", ")}`;
  }

  if (totalNet < 0) {
    const totalFormatted = formatMoney(Math.abs(totalNet), currency);
    const negParts = negScopes.map((s) => formatScopeItem(s, Math.abs(s.netUnits)));
    if (posScopes.length === 0) {
      return `You owe ${friendName} ${totalFormatted}: ${negParts.join(" + ")}`;
    }
    const posSum = posScopes.reduce((acc, s) => acc + s.netUnits, 0);
    const posParts = posScopes.map((s) => formatScopeItem(s, s.netUnits));
    return `You owe ${friendName} ${totalFormatted}: ${negParts.join(" + ")} · offset by ${formatMoney(posSum, currency)} ${friendName} owes you directly/from ${posParts.join(", ")}`;
  }

  // totalNet === 0 with mixed non-zero scopes
  const posParts = posScopes.map((s) => formatScopeItem(s, s.netUnits));
  const negParts = negScopes.map((s) => formatScopeItem(s, Math.abs(s.netUnits)));
  return `Balances offset to ${formatMoney(0, currency)}: ${friendName} owes you ${posParts.join(", ")} · You owe ${friendName} ${negParts.join(", ")}`;
}

export function calculateFriendScopeBreakdown(params: {
  myUid: string;
  friendUid: string;
  friendName: string;
  directExpenses: DirectExpenseInput[];
  directSettlements: DirectSettlementInput[];
  sharedGroups: SharedGroupInput[];
}): {
  breakdownsByCurrency: Record<string, CurrencyBalanceBreakdown>;
  transactions: FriendLedgerTransaction[];
} {
  const { myUid, friendUid, friendName, directExpenses, directSettlements, sharedGroups } = params;

  const transactionsMap = new Map<string, FriendLedgerTransaction>();
  const seenExpenseIds = new Set<string>();
  const seenSettlementIds = new Set<string>();
  const currencyScopeMap = new Map<
    string,
    Map<string, { scopeName: string; isDirect: boolean; netUnits: number }>
  >();

  const getScopeEntry = (curr: string, scopeId: string, scopeName: string, isDirect: boolean) => {
    let currMap = currencyScopeMap.get(curr);
    if (!currMap) {
      currMap = new Map();
      currencyScopeMap.set(curr, currMap);
    }
    let entry = currMap.get(scopeId);
    if (!entry) {
      entry = { scopeName, isDirect, netUnits: 0 };
      currMap.set(scopeId, entry);
    }
    return entry;
  };

  // 1. Process Direct Expenses (prevent double-counting duplicate IDs)
  for (const de of directExpenses) {
    if (!de.id || seenExpenseIds.has(de.id)) continue;
    seenExpenseIds.add(de.id);

    const curr = (de.currency || "AED").toUpperCase();
    const isPayerMe = de.paid_by_uid === myUid;
    const isPayerFriend = de.paid_by_uid === friendUid;

    const mySplit = de.splits.find((s) => s.user_id === myUid)?.amount_units ?? 0;
    const friendSplit = de.splits.find((s) => s.user_id === friendUid)?.amount_units ?? 0;

    let netImpact = 0;
    if (isPayerMe) {
      netImpact = friendSplit;
    } else if (isPayerFriend) {
      netImpact = -mySplit;
    }

    const entry = getScopeEntry(curr, "direct", "Direct", true);
    entry.netUnits += netImpact;

    transactionsMap.set(`exp_${de.id}`, {
      id: de.id,
      type: "expense",
      scope: "direct",
      friendshipId: de.friendship_id ?? null,
      date: de.expense_date,
      description: de.description,
      category: de.category,
      currency: curr,
      amountUnits: de.amount_units,
      paidByUid: de.paid_by_uid,
      paidByName: isPayerMe ? "You" : friendName,
      netImpactForUser: netImpact,
      userShareUnits: mySplit,
      friendShareUnits: friendSplit,
      note: de.note ?? null,
      rawExpense: de,
    });
  }

  // 2. Process Direct Settlements (prevent double-counting duplicate IDs)
  for (const ds of directSettlements) {
    if (!ds.id || seenSettlementIds.has(ds.id)) continue;
    seenSettlementIds.add(ds.id);

    const curr = (ds.currency || "AED").toUpperCase();
    const fromMe = ds.from_uid === myUid;
    const fromFriend = ds.from_uid === friendUid;

    let netImpact = 0;
    if (fromMe && ds.to_uid === friendUid) {
      netImpact = ds.amount_units;
    } else if (fromFriend && ds.to_uid === myUid) {
      netImpact = -ds.amount_units;
    }

    const entry = getScopeEntry(curr, "direct", "Direct", true);
    entry.netUnits += netImpact;

    transactionsMap.set(`set_${ds.id}`, {
      id: ds.id,
      type: "settlement",
      scope: "direct",
      friendshipId: ds.friendship_id ?? null,
      date: ds.settled_on,
      description: `Payment: ${formatMoney(ds.amount_units, curr)}`,
      currency: curr,
      amountUnits: ds.amount_units,
      paidByUid: ds.from_uid,
      paidByName: fromMe ? "You" : friendName,
      netImpactForUser: netImpact,
      userShareUnits: 0,
      friendShareUnits: 0,
      fromUid: ds.from_uid,
      toUid: ds.to_uid,
      note: ds.note ?? null,
      rawSettlement: ds,
    });
  }

  // 3. Process Shared Groups
  for (const grp of sharedGroups) {
    const myMem = grp.members.find((m) => m.user_id === myUid);
    const friendMem = grp.members.find((m) => m.user_id === friendUid);
    const myMemId = myMem?.id;
    const friendMemId = friendMem?.id;

    // A. Group Expenses (prevent double-counting duplicate IDs)
    for (const ge of grp.expenses) {
      if (!ge.id || seenExpenseIds.has(ge.id)) continue;
      seenExpenseIds.add(ge.id);

      const curr = (ge.currency || "AED").toUpperCase();
      const isPayerMe = ge.paid_by_uid === myUid || (myMemId && ge.paid_by_member_id === myMemId);
      const isPayerFriend =
        ge.paid_by_uid === friendUid || (friendMemId && ge.paid_by_member_id === friendMemId);

      const mySplit =
        ge.splits.find((s) => s.user_id === myUid || (myMemId && s.member_id === myMemId))
          ?.amount_units ?? 0;
      const friendSplit =
        ge.splits.find(
          (s) => s.user_id === friendUid || (friendMemId && s.member_id === friendMemId),
        )?.amount_units ?? 0;

      let netImpact = 0;
      if (isPayerMe) {
        netImpact = friendSplit;
      } else if (isPayerFriend) {
        netImpact = -mySplit;
      }

      const involvesBoth =
        (isPayerMe && friendSplit > 0) ||
        (isPayerFriend && mySplit > 0) ||
        (mySplit > 0 && friendSplit > 0) ||
        (ge.participant_uids?.includes(myUid) && ge.participant_uids?.includes(friendUid));

      if (involvesBoth || netImpact !== 0) {
        if (netImpact !== 0) {
          const entry = getScopeEntry(curr, grp.id, grp.name, false);
          entry.netUnits += netImpact;
        }

        const payerName = isPayerMe
          ? "You"
          : isPayerFriend
            ? friendName
            : grp.members.find((m) => m.user_id === ge.paid_by_uid || m.id === ge.paid_by_member_id)
                ?.name || "Group member";

        transactionsMap.set(`exp_${ge.id}`, {
          id: ge.id,
          type: "expense",
          scope: "group",
          groupId: grp.id,
          groupName: grp.name,
          date: ge.expense_date,
          description: ge.description,
          category: ge.category,
          currency: curr,
          amountUnits: ge.amount_units,
          paidByUid: ge.paid_by_uid,
          paidByName: payerName,
          netImpactForUser: netImpact,
          userShareUnits: mySplit,
          friendShareUnits: friendSplit,
          note: ge.note ?? null,
          rawExpense: ge,
        });
      }
    }

    // B. Group Settlements (prevent double-counting duplicate IDs)
    for (const gs of grp.settlements) {
      if (!gs.id || seenSettlementIds.has(gs.id)) continue;
      seenSettlementIds.add(gs.id);

      const curr = (gs.currency || "AED").toUpperCase();
      const fromMe = gs.from_uid === myUid || (myMemId && gs.from_member_id === myMemId);
      const toFriend = gs.to_uid === friendUid || (friendMemId && gs.to_member_id === friendMemId);

      const fromFriend =
        gs.from_uid === friendUid || (friendMemId && gs.from_member_id === friendMemId);
      const toMe = gs.to_uid === myUid || (myMemId && gs.to_member_id === myMemId);

      if ((fromMe && toFriend) || (fromFriend && toMe)) {
        let netImpact = 0;
        if (fromMe && toFriend) {
          netImpact = gs.amount_units;
        } else if (fromFriend && toMe) {
          netImpact = -gs.amount_units;
        }

        const entry = getScopeEntry(curr, grp.id, grp.name, false);
        entry.netUnits += netImpact;

        transactionsMap.set(`set_${gs.id}`, {
          id: gs.id,
          type: "settlement",
          scope: "group",
          groupId: grp.id,
          groupName: grp.name,
          date: gs.settled_on,
          description: `Payment: ${formatMoney(gs.amount_units, curr)}`,
          currency: curr,
          amountUnits: gs.amount_units,
          paidByUid: gs.from_uid,
          paidByName: fromMe ? "You" : friendName,
          netImpactForUser: netImpact,
          userShareUnits: 0,
          friendShareUnits: 0,
          fromUid: gs.from_uid,
          toUid: gs.to_uid,
          note: gs.note ?? null,
          rawSettlement: gs,
        });
      }
    }
  }

  // 4. Construct Currency Balance Breakdowns
  const breakdownsByCurrency: Record<string, CurrencyBalanceBreakdown> = {};

  for (const [curr, scopeMap] of currencyScopeMap.entries()) {
    const scopes: ScopeBreakdownItem[] = [];
    let totalNetUnits = 0;
    let userOwesFriendUnits = 0;
    let friendOwesUserUnits = 0;

    for (const [scopeId, scopeData] of scopeMap.entries()) {
      const net = scopeData.netUnits;
      totalNetUnits += net;
      const userOwes = net < 0 ? Math.abs(net) : 0;
      const friendOwes = net > 0 ? net : 0;
      userOwesFriendUnits += userOwes;
      friendOwesUserUnits += friendOwes;

      scopes.push({
        scopeId,
        scopeName: scopeData.scopeName,
        isDirect: scopeData.isDirect,
        netUnits: net,
        userOwesFriendUnits: userOwes,
        friendOwesUserUnits: friendOwes,
      });
    }

    const explanation = formatPlainBalanceExplanation(friendName, curr, scopes, totalNetUnits);

    breakdownsByCurrency[curr] = {
      currency: curr,
      totalNetUnits,
      userOwesFriendUnits,
      friendOwesUserUnits,
      scopes,
      explanation,
    };
  }

  const transactions = Array.from(transactionsMap.values()).sort((a, b) =>
    b.date.localeCompare(a.date),
  );

  return { breakdownsByCurrency, transactions };
}

export function filterTransactionsByScope(
  transactions: FriendLedgerTransaction[],
  scopeFilter: "all" | "direct" | "shared_all" | string,
  typeFilter: "all" | "expenses" | "settlements" = "all",
): FriendLedgerTransaction[] {
  return transactions.filter((t) => {
    if (scopeFilter === "direct" && t.scope !== "direct") return false;
    if (scopeFilter === "shared_all" && t.scope !== "group") return false;
    if (
      scopeFilter !== "all" &&
      scopeFilter !== "direct" &&
      scopeFilter !== "shared_all" &&
      t.groupId !== scopeFilter
    )
      return false;

    if (typeFilter === "expenses" && t.type !== "expense") return false;
    if (typeFilter === "settlements" && t.type !== "settlement") return false;

    return true;
  });
}

export function calculateResultingBalance(params: {
  currentNetUnits: number; // > 0: friend owes user, < 0: user owes friend, 0: settled
  direction: "user_paid_friend" | "friend_paid_user";
  paymentUnits: number;
  currency: string;
  friendName: string;
}): {
  resultingNetUnits: number;
  remainingUnits: number;
  status: "settled" | "partial" | "overpaid" | "advance";
  label: string;
} {
  const { currentNetUnits, direction, paymentUnits, currency, friendName } = params;
  const payer = direction === "user_paid_friend" ? "user" : "friend";

  const resultingNetUnits =
    payer === "user" ? currentNetUnits + paymentUnits : currentNetUnits - paymentUnits;

  if (!Number.isFinite(paymentUnits) || paymentUnits < 0) {
    return {
      resultingNetUnits: currentNetUnits,
      remainingUnits: Math.abs(currentNetUnits),
      status: "partial",
      label: "",
    };
  }

  if (paymentUnits === 0) {
    const currentAbs = Math.abs(currentNetUnits);
    let label = `No change: balance remains ${formatMoney(currentAbs, currency)}`;
    if (currentNetUnits > 0) label += ` owed by ${friendName}`;
    else if (currentNetUnits < 0) label += ` owed by you`;
    else label = `Settled (${formatMoney(0, currency)})`;
    return {
      resultingNetUnits: currentNetUnits,
      remainingUnits: currentAbs,
      status: currentNetUnits === 0 ? "settled" : "partial",
      label,
    };
  }

  if (resultingNetUnits === 0) {
    return {
      resultingNetUnits: 0,
      remainingUnits: 0,
      status: "settled",
      label: `Fully settled (${formatMoney(0, currency)})`,
    };
  }

  if (resultingNetUnits > 0) {
    if (currentNetUnits < 0) {
      return {
        resultingNetUnits,
        remainingUnits: resultingNetUnits,
        status: "overpaid",
        label: `Overpayment: ${friendName} will owe you ${formatMoney(resultingNetUnits, currency)} as credit`,
      };
    }
    if (payer === "user" && currentNetUnits >= 0) {
      return {
        resultingNetUnits,
        remainingUnits: resultingNetUnits,
        status: "advance",
        label: `Advance: ${friendName} will owe you ${formatMoney(resultingNetUnits, currency)}`,
      };
    }
    return {
      resultingNetUnits,
      remainingUnits: resultingNetUnits,
      status: "partial",
      label: `${friendName} will still owe you ${formatMoney(resultingNetUnits, currency)}`,
    };
  }

  const absRemaining = Math.abs(resultingNetUnits);
  if (currentNetUnits > 0) {
    return {
      resultingNetUnits,
      remainingUnits: absRemaining,
      status: "overpaid",
      label: `Overpayment: You will owe ${friendName} ${formatMoney(absRemaining, currency)} as credit`,
    };
  }
  if (payer === "friend" && currentNetUnits <= 0) {
    return {
      resultingNetUnits,
      remainingUnits: absRemaining,
      status: "advance",
      label: `Advance: You will owe ${friendName} ${formatMoney(absRemaining, currency)}`,
    };
  }
  return {
    resultingNetUnits,
    remainingUnits: absRemaining,
    status: "partial",
    label: `You will still owe ${friendName} ${formatMoney(absRemaining, currency)}`,
  };
}

export function generatePreSaveSplitSummary(params: {
  totalUnits: number;
  currency: string;
  payerId: string;
  myId: string;
  members: { id: string; name: string }[];
  shares: Share[];
}): string | null {
  const { totalUnits, currency, payerId, myId, members, shares } = params;
  if (!Number.isFinite(totalUnits) || totalUnits <= 0 || !shares || shares.length === 0)
    return null;
  if (shares.some((s) => !Number.isFinite(s.cents) || s.cents < 0)) return null;

  const sumShares = shares.reduce((acc, s) => acc + s.cents, 0);
  if (sumShares !== totalUnits) return null;

  const payerMember = members.find((m) => m.id === payerId);
  const isMe = payerId === myId;
  const payerName = isMe ? "You" : payerMember?.name || "Payer";
  const totalFormatted = formatMoney(totalUnits, currency);

  const activeShares = shares.filter((s) => s.cents > 0);

  if (activeShares.length === 1 && activeShares[0]?.memberId === payerId) {
    if (isMe) {
      return `You paid ${totalFormatted} for yourself. Personal expense (no balance impact).`;
    }
    return `${payerName} paid ${totalFormatted} for themselves (no balance impact).`;
  }

  if (isMe) {
    const others = activeShares.filter((s) => s.memberId !== myId);
    if (others.length === 0) {
      return `You paid ${totalFormatted} for yourself. Personal expense (no balance impact).`;
    }
    const details = others.map((o) => {
      const name = members.find((m) => m.id === o.memberId)?.name || "Member";
      return `${name} owes you ${formatMoney(o.cents, currency)}`;
    });
    if (details.length === 1) {
      return `You paid ${totalFormatted}. ${details[0]}.`;
    }
    return `You paid ${totalFormatted}. ${details.slice(0, -1).join(", ")} and ${details[details.length - 1]}.`;
  } else {
    const myShare = activeShares.find((s) => s.memberId === myId)?.cents ?? 0;
    if (myShare > 0) {
      return `${payerName} paid ${totalFormatted}. You owe ${payerName} ${formatMoney(myShare, currency)}.`;
    }
    return `${payerName} paid ${totalFormatted}. You owe nothing.`;
  }
}
