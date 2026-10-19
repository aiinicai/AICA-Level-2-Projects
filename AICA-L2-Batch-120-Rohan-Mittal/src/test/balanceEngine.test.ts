import { describe, expect, it } from "vitest";
import {
  netBalances,
  netBalancesByCurrency,
  simplifyDebts,
  splitEqual,
  splitPercentage,
  calculatePairwiseBalances,
  calculateFriendScopeBreakdown,
  calculateResultingBalance,
  filterTransactionsByScope,
  generatePreSaveSplitSummary,
  type FriendLedgerTransaction,
} from "../lib/balanceEngine";
import { toMinorUnits, fromMinorUnits, formatMoney } from "@/lib/currencies";
import { sanitizeCell } from "@/lib/exportExcel";

describe("balanceEngine core", () => {
  it("keeps penny parity", () => {
    const eq = splitEqual(1000, ["a", "b", "c"], "b");
    expect(eq.ok && eq.shares.reduce((s, x) => s + x.cents, 0)).toBe(1000);
    expect(eq.ok && eq.shares.find((s) => s.memberId === "b")!.cents).toBe(334);
    const pc = splitPercentage(1001, [
      { memberId: "a", pct: 33.33 },
      { memberId: "b", pct: 33.33 },
      { memberId: "c", pct: 33.34 },
    ]);
    expect(pc.ok && pc.shares.reduce((s, x) => s + x.cents, 0)).toBe(1001);
  });

  it("net balances sum to zero and simplify clears all", () => {
    const s1 = splitEqual(9000, ["a", "b", "c"], "a");
    const s2 = splitEqual(1001, ["b", "c"], "c");
    if (!s1.ok || !s2.ok) throw new Error();
    const net = netBalances(
      ["a", "b", "c"],
      [
        { paidBy: "a", cents: 9000, shares: s1.shares },
        { paidBy: "c", cents: 1001, shares: s2.shares },
      ],
      [{ from: "b", to: "a", cents: 500 }],
    );
    expect(Object.values(net).reduce((s, v) => s + v, 0)).toBe(0);
    const after = { ...net };
    for (const t of simplifyDebts(net)) {
      after[t.from] = (after[t.from] ?? 0) + t.cents;
      after[t.to] = (after[t.to] ?? 0) - t.cents;
    }
    expect(Object.values(after).every((v) => v === 0)).toBe(true);
  });

  it("rounds equal splits with payer outside participants", () => {
    const r = splitEqual(1001, ["a", "b", "c"], "z");
    expect(r.ok && r.shares.map((s) => s.cents)).toEqual([334, 334, 333]);
  });

  it("validates exact and percentage totals", async () => {
    const { splitExact } = await import("@/lib/balanceEngine");
    expect(
      splitExact(1000, [
        { memberId: "a", cents: 500 },
        { memberId: "b", cents: 499 },
      ]).ok,
    ).toBe(false);
    expect(
      splitExact(1000, [
        { memberId: "a", cents: 1200 },
        { memberId: "b", cents: -200 },
      ]).ok,
    ).toBe(false);
    expect(
      splitPercentage(1000, [
        { memberId: "a", pct: 50 },
        { memberId: "b", pct: 49 },
      ]).ok,
    ).toBe(false);
    const p = splitPercentage(
      1000,
      [
        { memberId: "a", pct: 33.33 },
        { memberId: "b", pct: 33.33 },
        { memberId: "c", pct: 33.34 },
      ],
      "b",
    );
    expect(p.ok && p.shares.reduce((s, x) => s + x.cents, 0)).toBe(1000);
  });

  it("partial settlement reduces the suggested payment", () => {
    const s = splitEqual(6000, ["a", "b"], "a");
    if (!s.ok) throw new Error();
    const exp = [{ paidBy: "a", cents: 6000, shares: s.shares }];
    expect(simplifyDebts(netBalances(["a", "b"], exp, []))).toEqual([
      { from: "b", to: "a", cents: 3000 },
    ]);
    expect(
      simplifyDebts(netBalances(["a", "b"], exp, [{ from: "b", to: "a", cents: 1000 }])),
    ).toEqual([{ from: "b", to: "a", cents: 2000 }]);
    expect(
      simplifyDebts(netBalances(["a", "b"], exp, [{ from: "b", to: "a", cents: 3000 }])),
    ).toEqual([]);
  });
});

describe("multi-currency and precision engine", () => {
  it("converts JPY (0 decimals) correctly", () => {
    expect(toMinorUnits(500, "JPY")).toBe(500);
    expect(fromMinorUnits(500, "JPY")).toBe(500);
  });

  it("converts KWD (3 decimals) correctly", () => {
    expect(toMinorUnits("1.500", "KWD")).toBe(1500);
    expect(fromMinorUnits(1500, "KWD")).toBe(1.5);
  });

  it("converts USD and AED (2 decimals) correctly", () => {
    expect(toMinorUnits("12.34", "USD")).toBe(1234);
    expect(fromMinorUnits(1234, "USD")).toBe(12.34);
    expect(toMinorUnits("99.99", "AED")).toBe(9999);
  });

  it("keeps multi-currency balances completely separate without cross-currency netting", () => {
    const expenses = [
      {
        paidBy: "userA",
        cents: 10000, // 100.00 AED
        currency: "AED",
        shares: [
          { memberId: "userA", cents: 5000 },
          { memberId: "userB", cents: 5000 },
        ],
      },
      {
        paidBy: "userB",
        cents: 2000, // 20.00 USD
        currency: "USD",
        shares: [
          { memberId: "userA", cents: 1000 },
          { memberId: "userB", cents: 1000 },
        ],
      },
    ];

    const netByCurr = netBalancesByCurrency(["userA", "userB"], expenses, []);
    expect(netByCurr["AED"]).toEqual({ userA: 5000, userB: -5000 });
    expect(netByCurr["USD"]).toEqual({ userA: -1000, userB: 1000 });
  });

  it("calculates exact pairwise balances between two users", () => {
    const expenses = [
      {
        paidBy: "userA",
        cents: 6000,
        currency: "EUR",
        shares: [
          { memberId: "userA", cents: 3000 },
          { memberId: "userB", cents: 3000 },
        ],
      },
    ];
    const settlements = [
      {
        from: "userB",
        to: "userA",
        cents: 1000,
        currency: "EUR",
      },
    ];
    const pairwise = calculatePairwiseBalances("userA", "userB", expenses, settlements);
    // User B owes User A 3000 - 1000 = 2000 EUR
    expect(pairwise["EUR"]).toBe(2000);
  });
});

describe("security & export formatting", () => {
  it("sanitizes potential formula injections in Excel exports", () => {
    expect(sanitizeCell("=SUM(A1:A10)")).toBe("'=SUM(A1:A10)");
    expect(sanitizeCell("+12345")).toBe("'+12345");
    expect(sanitizeCell("-@DROP TABLE")).toBe("'-@DROP TABLE");
    expect(sanitizeCell("@calc")).toBe("'@calc");
    expect(sanitizeCell("Normal dinner")).toBe("Normal dinner");
  });
});

describe("friend ledger aggregation, resulting balances & plain explanations", () => {
  it("aggregates direct and shared groups with plain explanation", () => {
    const directExpenses = [
      {
        id: "de1",
        description: "Coffee",
        amount_units: 12000, // 120 AED
        currency: "AED",
        paid_by_uid: "my_uid",
        expense_date: "2026-10-15",
        splits: [
          { user_id: "my_uid", amount_units: 6000 },
          { user_id: "friend_uid", amount_units: 6000 },
        ],
      },
    ];

    const sharedGroups = [
      {
        id: "g_europe",
        name: "Europe Trip",
        members: [
          { id: "mem_me", user_id: "my_uid", name: "Me" },
          { id: "mem_friend", user_id: "friend_uid", name: "Sara" },
        ],
        expenses: [
          {
            id: "ge1",
            description: "Museum tickets",
            amount_units: 24000, // 240 AED
            currency: "AED",
            paid_by_uid: "my_uid",
            paid_by_member_id: "mem_me",
            expense_date: "2026-10-16",
            splits: [
              { member_id: "mem_me", user_id: "my_uid", amount_units: 12000 },
              { member_id: "mem_friend", user_id: "friend_uid", amount_units: 12000 },
            ],
          },
        ],
        settlements: [],
      },
    ];

    const res = calculateFriendScopeBreakdown({
      myUid: "my_uid",
      friendUid: "friend_uid",
      friendName: "Sara",
      directExpenses,
      directSettlements: [],
      sharedGroups,
    });

    const aed = res.breakdownsByCurrency["AED"];
    expect(aed).toBeDefined();
    // 6000 (60 AED) direct + 12000 (120 AED) Europe Trip = 18000 (180 AED)
    expect(aed!.totalNetUnits).toBe(18000);
    expect(aed!.scopes.length).toBe(2);
    expect(aed!.explanation).toContain("Sara owes you");
    expect(aed!.explanation).toContain("directly");
    expect(aed!.explanation).toContain("Europe Trip");
    expect(res.transactions.length).toBe(2);
  });

  it("handles mixed owed and owing scopes that offset to zero without losing scope details", () => {
    const directExpenses = [
      {
        id: "de1",
        description: "Dinner",
        amount_units: 12000,
        currency: "AED",
        paid_by_uid: "my_uid", // I paid -> Sara owes 60
        expense_date: "2026-10-15",
        splits: [
          { user_id: "my_uid", amount_units: 6000 },
          { user_id: "friend_uid", amount_units: 6000 },
        ],
      },
    ];

    const sharedGroups = [
      {
        id: "g_europe",
        name: "Europe Trip",
        members: [
          { id: "mem_me", user_id: "my_uid", name: "Me" },
          { id: "mem_friend", user_id: "friend_uid", name: "Sara" },
        ],
        expenses: [
          {
            id: "ge1",
            description: "Train pass",
            amount_units: 12000,
            currency: "AED",
            paid_by_uid: "friend_uid", // Sara paid -> I owe 60
            expense_date: "2026-10-16",
            splits: [
              { member_id: "mem_me", user_id: "my_uid", amount_units: 6000 },
              { member_id: "mem_friend", user_id: "friend_uid", amount_units: 6000 },
            ],
          },
        ],
        settlements: [],
      },
    ];

    const res = calculateFriendScopeBreakdown({
      myUid: "my_uid",
      friendUid: "friend_uid",
      friendName: "Sara",
      directExpenses,
      directSettlements: [],
      sharedGroups,
    });

    const aed = res.breakdownsByCurrency["AED"];
    expect(aed).toBeDefined();
    expect(aed!.totalNetUnits).toBe(0);
    expect(aed!.explanation).toContain("Balances offset to");
    expect(aed!.explanation).toContain("directly");
    expect(aed!.explanation).toContain("Europe Trip");
  });

  it("calculates resulting balance on settlement for full, partial, overpayment, and reversed direction", () => {
    // Case 1: I owe Sara 100 AED. I pay full 100.
    const full = calculateResultingBalance({
      currentNetUnits: -10000,
      direction: "user_paid_friend",
      paymentUnits: 10000,
      currency: "AED",
      friendName: "Sara",
    });
    expect(full.resultingNetUnits).toBe(0);
    expect(full.status).toBe("settled");
    expect(full.label).toContain("Fully settled");

    // Case 2: I owe Sara 100 AED. I pay partial 40 AED.
    const partial = calculateResultingBalance({
      currentNetUnits: -10000,
      direction: "user_paid_friend",
      paymentUnits: 4000,
      currency: "AED",
      friendName: "Sara",
    });
    expect(partial.resultingNetUnits).toBe(-6000);
    expect(partial.status).toBe("partial");
    expect(partial.label).toContain("You will still owe Sara");

    // Case 3: I owe Sara 100 AED. I pay 150 AED (overpayment).
    const over = calculateResultingBalance({
      currentNetUnits: -10000,
      direction: "user_paid_friend",
      paymentUnits: 15000,
      currency: "AED",
      friendName: "Sara",
    });
    expect(over.resultingNetUnits).toBe(5000);
    expect(over.status).toBe("overpaid");
    expect(over.label).toContain("Overpayment");

    // Case 4: Sara owes me 60 AED. Sara pays 60 AED.
    const friendPaidFull = calculateResultingBalance({
      currentNetUnits: 6000,
      direction: "friend_paid_user",
      paymentUnits: 6000,
      currency: "AED",
      friendName: "Sara",
    });
    expect(friendPaidFull.resultingNetUnits).toBe(0);
    expect(friendPaidFull.status).toBe("settled");

    // Case 5: Zero balance. User pays 50 AED in advance.
    const advance = calculateResultingBalance({
      currentNetUnits: 0,
      direction: "user_paid_friend",
      paymentUnits: 5000,
      currency: "AED",
      friendName: "Sara",
    });
    expect(advance.resultingNetUnits).toBe(5000);
    expect(advance.status).toBe("advance");
  });

  it("filters transactions accurately by scope and type", () => {
    const sample: FriendLedgerTransaction[] = [
      {
        id: "1",
        type: "expense",
        scope: "direct",
        groupId: null,
        date: "2026-10-10",
        description: "Coffee",
        currency: "AED",
        amountUnits: 1000,
        paidByUid: "u1",
        netImpactForUser: 500,
        userShareUnits: 500,
        friendShareUnits: 500,
      },
      {
        id: "2",
        type: "settlement",
        scope: "direct",
        groupId: null,
        date: "2026-10-11",
        description: "Payment",
        currency: "AED",
        amountUnits: 500,
        paidByUid: "u2",
        netImpactForUser: 500,
        userShareUnits: 0,
        friendShareUnits: 0,
      },
      {
        id: "3",
        type: "expense",
        scope: "group",
        groupId: "grp1",
        date: "2026-10-12",
        description: "Lunch",
        currency: "AED",
        amountUnits: 2000,
        paidByUid: "u1",
        netImpactForUser: 1000,
        userShareUnits: 1000,
        friendShareUnits: 1000,
      },
      {
        id: "4",
        type: "settlement",
        scope: "group",
        groupId: "grp1",
        date: "2026-10-13",
        description: "Group Payment",
        currency: "AED",
        amountUnits: 1000,
        paidByUid: "u2",
        netImpactForUser: 1000,
        userShareUnits: 0,
        friendShareUnits: 0,
      },
      {
        id: "5",
        type: "expense",
        scope: "group",
        groupId: "grp2",
        date: "2026-10-14",
        description: "Dinner",
        currency: "AED",
        amountUnits: 3000,
        paidByUid: "u1",
        netImpactForUser: 1500,
        userShareUnits: 1500,
        friendShareUnits: 1500,
      },
    ];

    expect(filterTransactionsByScope(sample, "all", "all").length).toBe(5);
    expect(filterTransactionsByScope(sample, "direct", "all").length).toBe(2);
    expect(filterTransactionsByScope(sample, "grp1", "all").length).toBe(2);
    expect(filterTransactionsByScope(sample, "all", "expenses").length).toBe(3);
    expect(filterTransactionsByScope(sample, "all", "settlements").length).toBe(2);
    expect(filterTransactionsByScope(sample, "direct", "settlements").length).toBe(1);
  });

  it("generates live accurate pre-save split summary", () => {
    const members = [
      { id: "user_me", name: "You" },
      { id: "user_sara", name: "Sara" },
      { id: "user_omar", name: "Omar" },
    ];

    // Case 1: You paid 120, Sara owes 60 (2-way equal)
    const s1 = generatePreSaveSplitSummary({
      totalUnits: 12000,
      currency: "AED",
      payerId: "user_me",
      myId: "user_me",
      members,
      shares: [
        { memberId: "user_me", cents: 6000 },
        { memberId: "user_sara", cents: 6000 },
      ],
    });
    expect(s1).toContain("You paid");
    expect(s1).toContain("Sara owes you");

    // Case 2: Sara paid 120, You owe Sara 60
    const s2 = generatePreSaveSplitSummary({
      totalUnits: 12000,
      currency: "AED",
      payerId: "user_sara",
      myId: "user_me",
      members,
      shares: [
        { memberId: "user_me", cents: 6000 },
        { memberId: "user_sara", cents: 6000 },
      ],
    });
    expect(s2).toContain("Sara paid");
    expect(s2).toContain("You owe Sara");

    // Case 3: You paid 150, 3-way split (50 each)
    const s3 = generatePreSaveSplitSummary({
      totalUnits: 15000,
      currency: "AED",
      payerId: "user_me",
      myId: "user_me",
      members,
      shares: [
        { memberId: "user_me", cents: 5000 },
        { memberId: "user_sara", cents: 5000 },
        { memberId: "user_omar", cents: 5000 },
      ],
    });
    expect(s3).toContain("Sara owes you");
    expect(s3).toContain("Omar owes you");

    // Case 4: Single participant (personal expense)
    const s4 = generatePreSaveSplitSummary({
      totalUnits: 5000,
      currency: "AED",
      payerId: "user_me",
      myId: "user_me",
      members,
      shares: [{ memberId: "user_me", cents: 5000 }],
    });
    expect(s4).toContain("Personal expense");

    // Case 5: Zero or invalid shares returns null
    const s5 = generatePreSaveSplitSummary({
      totalUnits: 0,
      currency: "AED",
      payerId: "user_me",
      myId: "user_me",
      members,
      shares: [],
    });
    expect(s5).toBeNull();

    // Case 6: Sum of shares mismatch (e.g. allocated 100 but total is 120) returns null
    const s6 = generatePreSaveSplitSummary({
      totalUnits: 12000,
      currency: "AED",
      payerId: "user_me",
      myId: "user_me",
      members,
      shares: [
        { memberId: "user_me", cents: 5000 },
        { memberId: "user_sara", cents: 5000 },
      ],
    });
    expect(s6).toBeNull();

    // Case 7: Negative share value returns null
    const s7 = generatePreSaveSplitSummary({
      totalUnits: 10000,
      currency: "AED",
      payerId: "user_me",
      myId: "user_me",
      members,
      shares: [
        { memberId: "user_me", cents: 15000 },
        { memberId: "user_sara", cents: -5000 },
      ],
    });
    expect(s7).toBeNull();
  });

  it("regression: duplicate input expense or settlement IDs do not double-count balances", () => {
    const directExpenses = [
      {
        id: "dup_exp_1",
        description: "Dinner",
        amount_units: 10000,
        currency: "AED",
        paid_by_uid: "my_uid",
        expense_date: "2026-10-15",
        splits: [
          { user_id: "my_uid", amount_units: 5000 },
          { user_id: "friend_uid", amount_units: 5000 },
        ],
      },
      // Exact duplicate entry passed in array
      {
        id: "dup_exp_1",
        description: "Dinner",
        amount_units: 10000,
        currency: "AED",
        paid_by_uid: "my_uid",
        expense_date: "2026-10-15",
        splits: [
          { user_id: "my_uid", amount_units: 5000 },
          { user_id: "friend_uid", amount_units: 5000 },
        ],
      },
    ];

    const directSettlements = [
      {
        id: "dup_set_1",
        friendship_id: "f1",
        from_uid: "friend_uid",
        to_uid: "my_uid",
        amount_units: 2000,
        currency: "AED",
        settled_on: "2026-10-16",
      },
      // Exact duplicate settlement
      {
        id: "dup_set_1",
        friendship_id: "f1",
        from_uid: "friend_uid",
        to_uid: "my_uid",
        amount_units: 2000,
        currency: "AED",
        settled_on: "2026-10-16",
      },
    ];

    const res = calculateFriendScopeBreakdown({
      myUid: "my_uid",
      friendUid: "friend_uid",
      friendName: "Sara",
      directExpenses,
      directSettlements,
      sharedGroups: [],
    });

    const aed = res.breakdownsByCurrency["AED"];
    expect(aed).toBeDefined();
    // 5000 (owed by Sara) - 2000 (paid by Sara) = 3000 net (NOT 6000)
    expect(aed!.totalNetUnits).toBe(3000);
    expect(res.transactions.length).toBe(2);
  });

  it("formats zero balances correctly for JPY (0 decimals) and KWD (3 decimals)", () => {
    // JPY zero check in explanation
    const jpyBreakdown = calculateFriendScopeBreakdown({
      myUid: "my_uid",
      friendUid: "friend_uid",
      friendName: "Ken",
      directExpenses: [
        {
          id: "jpy_1",
          description: "Ramen",
          amount_units: 2000,
          currency: "JPY",
          paid_by_uid: "my_uid",
          expense_date: "2026-10-10",
          splits: [
            { user_id: "my_uid", amount_units: 1000 },
            { user_id: "friend_uid", amount_units: 1000 },
          ],
        },
      ],
      directSettlements: [
        {
          id: "jpy_set_1",
          from_uid: "friend_uid",
          to_uid: "my_uid",
          amount_units: 1000,
          currency: "JPY",
          settled_on: "2026-10-11",
        },
      ],
      sharedGroups: [],
    });

    const jpy = jpyBreakdown.breakdownsByCurrency["JPY"];
    expect(jpy).toBeDefined();
    expect(jpy!.totalNetUnits).toBe(0);

    // Resulting balance label check for JPY zero
    const jpyRes = calculateResultingBalance({
      currentNetUnits: 0,
      direction: "user_paid_friend",
      paymentUnits: 0,
      currency: "JPY",
      friendName: "Ken",
    });
    expect(jpyRes.label).not.toContain("0.00");
    expect(jpyRes.label).toContain("0");

    // Resulting balance label check for KWD zero
    const kwdRes = calculateResultingBalance({
      currentNetUnits: 0,
      direction: "user_paid_friend",
      paymentUnits: 0,
      currency: "KWD",
      friendName: "Ahmed",
    });
    expect(kwdRes.label).toContain("0.000");
  });

  it("filters shared_all correctly to all group transactions", () => {
    const sample: FriendLedgerTransaction[] = [
      {
        id: "1",
        type: "expense",
        scope: "direct",
        groupId: null,
        date: "2026-10-10",
        description: "Direct Coffee",
        currency: "AED",
        amountUnits: 1000,
        paidByUid: "u1",
        netImpactForUser: 500,
        userShareUnits: 500,
        friendShareUnits: 500,
      },
      {
        id: "2",
        type: "expense",
        scope: "group",
        groupId: "grp1",
        date: "2026-10-12",
        description: "Group Lunch",
        currency: "AED",
        amountUnits: 2000,
        paidByUid: "u1",
        netImpactForUser: 1000,
        userShareUnits: 1000,
        friendShareUnits: 1000,
      },
      {
        id: "3",
        type: "settlement",
        scope: "group",
        groupId: "grp2",
        date: "2026-10-13",
        description: "Group Payment",
        currency: "AED",
        amountUnits: 1000,
        paidByUid: "u2",
        netImpactForUser: 1000,
        userShareUnits: 0,
        friendShareUnits: 0,
      },
    ];

    const groupOnly = filterTransactionsByScope(sample, "shared_all", "all");
    expect(groupOnly.length).toBe(2);
    expect(groupOnly.every((t) => t.scope === "group")).toBe(true);
  });
});
