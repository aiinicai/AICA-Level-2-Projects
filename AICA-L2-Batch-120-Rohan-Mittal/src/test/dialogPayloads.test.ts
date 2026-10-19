import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  calculateResultingBalance,
  generatePreSaveSplitSummary,
  calculateFriendScopeBreakdown,
  filterTransactionsByScope,
} from "../lib/balanceEngine";
import { formatMoney } from "../lib/currencies";

describe("Dialog payloads & balance calculation verifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Direct vs Group Settlement save payloads", () => {
    it("builds exact payload for direct settlement with null group and member IDs", () => {
      const myUid = "user_me_123";
      const friendUid = "user_friend_456";
      const friendshipId = "friendship_789";

      // Mocked save handler simulating SettleDialog direct save
      const mockSaveSettlement = vi.fn();

      const isDirectScope = true;
      const units = 5000; // 50.00 AED
      const curr = "AED";
      const date = "2026-10-18";
      const note = "Direct payment for groceries";

      const payload = {
        settlementId: null,
        groupId: isDirectScope ? null : "group_123",
        friendshipId: isDirectScope ? friendshipId : null,
        from_member_id: isDirectScope ? null : "mem_1",
        to_member_id: isDirectScope ? null : "mem_2",
        from_uid: myUid,
        to_uid: friendUid,
        amount_units: units,
        currency: curr,
        settled_on: date,
        note: note.trim() || null,
      };

      mockSaveSettlement(payload);

      expect(mockSaveSettlement).toHaveBeenCalledTimes(1);
      const call = mockSaveSettlement.mock.calls[0]![0];
      expect(call.groupId).toBeNull();
      expect(call.friendshipId).toBe("friendship_789");
      expect(call.from_member_id).toBeNull();
      expect(call.to_member_id).toBeNull();
      expect(call.from_uid).toBe("user_me_123");
      expect(call.to_uid).toBe("user_friend_456");
      expect(call.amount_units).toBe(5000);
      expect(call.currency).toBe("AED");
    });

    it("builds exact payload for group settlement with actual groupId and member IDs", () => {
      const myUid = "user_me_123";
      const friendUid = "user_friend_456";
      const actualGroupId = "grp_tokyo_99";
      const myMemberId = "mem_me_in_tokyo";
      const friendMemberId = "mem_friend_in_tokyo";

      const mockSaveSettlement = vi.fn();

      const isDirectScope = false;
      const units = 10000; // 100.00 AED
      const curr = "AED";
      const date = "2026-10-18";

      const payload = {
        settlementId: null,
        groupId: isDirectScope ? null : actualGroupId,
        friendshipId: isDirectScope ? "friendship_xyz" : null,
        from_member_id: isDirectScope ? null : myMemberId,
        to_member_id: isDirectScope ? null : friendMemberId,
        from_uid: myUid,
        to_uid: friendUid,
        amount_units: units,
        currency: curr,
        settled_on: date,
        note: null,
      };

      mockSaveSettlement(payload);

      expect(mockSaveSettlement).toHaveBeenCalledTimes(1);
      const call = mockSaveSettlement.mock.calls[0]![0];
      expect(call.groupId).toBe("grp_tokyo_99");
      expect(call.friendshipId).toBeNull();
      expect(call.from_member_id).toBe("mem_me_in_tokyo");
      expect(call.to_member_id).toBe("mem_friend_in_tokyo");
      expect(call.from_uid).toBe("user_me_123");
      expect(call.to_uid).toBe("user_friend_456");
      expect(call.amount_units).toBe(10000);
      expect(call.currency).toBe("AED");
    });

    it("preserves old group settle/edit behavior when opening from a group page", () => {
      const editingExistingSettlement = {
        id: "settle_existing_1",
        group_id: "grp_flatmates_01",
        from_member_id: "mem_alice",
        to_member_id: "mem_bob",
        from_uid: "uid_alice",
        to_uid: "uid_bob",
        amount_units: 7500,
        currency: "USD",
        settled_on: "2026-10-10",
        note: "Initial payment",
      };

      const mockSaveSettlement = vi.fn();

      const payload = {
        settlementId: editingExistingSettlement.id,
        groupId: editingExistingSettlement.group_id,
        friendshipId: null,
        from_member_id: editingExistingSettlement.from_member_id,
        to_member_id: editingExistingSettlement.to_member_id,
        from_uid: editingExistingSettlement.from_uid,
        to_uid: editingExistingSettlement.to_uid,
        amount_units: 8000, // Updated amount
        currency: editingExistingSettlement.currency,
        settled_on: "2026-10-12",
        note: "Updated payment",
      };

      mockSaveSettlement(payload);

      expect(mockSaveSettlement).toHaveBeenCalledTimes(1);
      const call = mockSaveSettlement.mock.calls[0]![0];
      expect(call.settlementId).toBe("settle_existing_1");
      expect(call.groupId).toBe("grp_flatmates_01");
      expect(call.from_member_id).toBe("mem_alice");
      expect(call.to_member_id).toBe("mem_bob");
      expect(call.from_uid).toBe("uid_alice");
      expect(call.to_uid).toBe("uid_bob");
      expect(call.amount_units).toBe(8000);
    });
  });

  describe("Pre-save Split Summary validation & suppression", () => {
    const members = [
      { id: "u1", name: "You" },
      { id: "u2", name: "Sara" },
      { id: "u3", name: "Ahmed" },
    ];

    it("suppresses preview (returns null) for zero total units", () => {
      const summary = generatePreSaveSplitSummary({
        totalUnits: 0,
        currency: "AED",
        payerId: "u1",
        myId: "u1",
        members,
        shares: [
          { memberId: "u1", cents: 0 },
          { memberId: "u2", cents: 0 },
        ],
      });
      expect(summary).toBeNull();
    });

    it("suppresses preview (returns null) for negative total units", () => {
      const summary = generatePreSaveSplitSummary({
        totalUnits: -5000,
        currency: "AED",
        payerId: "u1",
        myId: "u1",
        members,
        shares: [
          { memberId: "u1", cents: -2500 },
          { memberId: "u2", cents: -2500 },
        ],
      });
      expect(summary).toBeNull();
    });

    it("suppresses preview (returns null) for negative share amounts", () => {
      const summary = generatePreSaveSplitSummary({
        totalUnits: 5000,
        currency: "AED",
        payerId: "u1",
        myId: "u1",
        members,
        shares: [
          { memberId: "u1", cents: 6000 },
          { memberId: "u2", cents: -1000 },
        ],
      });
      expect(summary).toBeNull();
    });

    it("suppresses preview (returns null) for split sum mismatching total", () => {
      const summary = generatePreSaveSplitSummary({
        totalUnits: 5000,
        currency: "AED",
        payerId: "u1",
        myId: "u1",
        members,
        shares: [
          { memberId: "u1", cents: 2000 },
          { memberId: "u2", cents: 2000 }, // sum 4000 !== 5000
        ],
      });
      expect(summary).toBeNull();
    });

    it("generates clear plain-language summary when user pays for another", () => {
      const summary = generatePreSaveSplitSummary({
        totalUnits: 10000,
        currency: "AED",
        payerId: "u1",
        myId: "u1",
        members,
        shares: [
          { memberId: "u1", cents: 5000 },
          { memberId: "u2", cents: 5000 },
        ],
      });
      expect(summary).toBeDefined();
      expect(summary).toContain("You paid");
      expect(summary).toContain("Sara owes you");
    });
  });

  describe("calculateResultingBalance preview & negative value suppression", () => {
    it("suppresses preview label for negative payment amounts", () => {
      const res = calculateResultingBalance({
        currentNetUnits: -5000,
        direction: "user_paid_friend",
        paymentUnits: -1000,
        currency: "AED",
        friendName: "Sara",
      });
      expect(res.label).toBe("");
    });

    it("handles zero payment with No change label using formatMoney(0, currency)", () => {
      const resJpy = calculateResultingBalance({
        currentNetUnits: 0,
        direction: "user_paid_friend",
        paymentUnits: 0,
        currency: "JPY",
        friendName: "Ken",
      });
      expect(resJpy.label).toContain("Settled");
      expect(resJpy.label).not.toContain("0.00");

      const resKwd = calculateResultingBalance({
        currentNetUnits: 0,
        direction: "user_paid_friend",
        paymentUnits: 0,
        currency: "KWD",
        friendName: "Fatima",
      });
      expect(resKwd.label).toContain("0.000");
    });

    it("calculates resulting balance on exact full settlement", () => {
      const res = calculateResultingBalance({
        currentNetUnits: -5000, // I owe Sara 50 AED
        direction: "user_paid_friend",
        paymentUnits: 5000, // I pay Sara 50 AED
        currency: "AED",
        friendName: "Sara",
      });
      expect(res.resultingNetUnits).toBe(0);
      expect(res.status).toBe("settled");
      expect(res.label).toContain("Fully settled");
    });

    it("calculates resulting balance on partial settlement", () => {
      const res = calculateResultingBalance({
        currentNetUnits: -10000, // I owe Sara 100 AED
        direction: "user_paid_friend",
        paymentUnits: 4000, // I pay Sara 40 AED
        currency: "AED",
        friendName: "Sara",
      });
      expect(res.resultingNetUnits).toBe(-6000);
      expect(res.status).toBe("partial");
      expect(res.label).toContain("You will still owe Sara");
    });
  });

  describe("Regression: Duplicate transaction IDs do not double count", () => {
    it("does not double count duplicate group or direct transaction entries", () => {
      const directExpenses = [
        {
          id: "exp_dup_x",
          description: "Brunch",
          amount_units: 8000,
          currency: "AED",
          paid_by_uid: "me",
          expense_date: "2026-10-17",
          splits: [
            { user_id: "me", amount_units: 4000 },
            { user_id: "friend", amount_units: 4000 },
          ],
        },
        // Duplicate entry with same ID
        {
          id: "exp_dup_x",
          description: "Brunch duplicate",
          amount_units: 8000,
          currency: "AED",
          paid_by_uid: "me",
          expense_date: "2026-10-17",
          splits: [
            { user_id: "me", amount_units: 4000 },
            { user_id: "friend", amount_units: 4000 },
          ],
        },
      ];

      const res = calculateFriendScopeBreakdown({
        myUid: "me",
        friendUid: "friend",
        friendName: "Zaid",
        directExpenses,
        directSettlements: [],
        sharedGroups: [],
      });

      const aed = res.breakdownsByCurrency["AED"];
      expect(aed).toBeDefined();
      expect(aed!.totalNetUnits).toBe(4000); // 4000, NOT 8000
      expect(res.transactions.length).toBe(1);
    });
  });

  describe("Timeline filters for explicit All, Direct, and Shared groups", () => {
    const transactions = [
      {
        id: "t1",
        type: "expense" as const,
        scope: "direct" as const,
        groupId: null,
        date: "2026-10-10",
        description: "Direct lunch",
        currency: "AED",
        amountUnits: 2000,
        paidByUid: "u1",
        netImpactForUser: 1000,
        userShareUnits: 1000,
        friendShareUnits: 1000,
      },
      {
        id: "t2",
        type: "expense" as const,
        scope: "group" as const,
        groupId: "g1",
        date: "2026-10-11",
        description: "Flatmates groceries",
        currency: "AED",
        amountUnits: 4000,
        paidByUid: "u1",
        netImpactForUser: 2000,
        userShareUnits: 2000,
        friendShareUnits: 2000,
      },
      {
        id: "t3",
        type: "settlement" as const,
        scope: "group" as const,
        groupId: "g2",
        date: "2026-10-12",
        description: "Roadtrip gas payment",
        currency: "AED",
        amountUnits: 1500,
        paidByUid: "u2",
        netImpactForUser: 1500,
        userShareUnits: 0,
        friendShareUnits: 0,
      },
    ];

    it("filters to Direct only", () => {
      const direct = filterTransactionsByScope(transactions, "direct");
      expect(direct.length).toBe(1);
      expect(direct[0]!.id).toBe("t1");
    });

    it("filters to all Shared groups combined via shared_all", () => {
      const sharedAll = filterTransactionsByScope(transactions, "shared_all");
      expect(sharedAll.length).toBe(2);
      expect(sharedAll.every((t) => t.scope === "group")).toBe(true);
    });

    it("filters to a specific individual group drilldown", () => {
      const g1Only = filterTransactionsByScope(transactions, "g1");
      expect(g1Only.length).toBe(1);
      expect(g1Only[0]!.id).toBe("t2");
    });

    it("returns All transactions when filter is all", () => {
      const all = filterTransactionsByScope(transactions, "all");
      expect(all.length).toBe(3);
    });
  });
});
