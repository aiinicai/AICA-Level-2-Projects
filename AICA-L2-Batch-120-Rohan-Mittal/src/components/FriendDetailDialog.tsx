import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Filter,
  Layers,
  Plus,
  Receipt,
  User,
  Users,
  Wallet,
  X,
} from "lucide-react";
import { formatMoney, fromMinorUnits } from "@/lib/currencies";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { MemberAvatar } from "@/components/AppShell";
import { type GroupData, type FriendSummary, type ExpenseRow } from "@/lib/app";
import {
  calculateFriendScopeBreakdown,
  filterTransactionsByScope,
  type FriendLedgerTransaction,
} from "@/lib/balanceEngine";

export function FriendDetailDialog({
  friend,
  groups,
  myUid,
  open,
  onOpenChange,
  onSettleUp,
  onAddDirectExpense,
  onEditDirectExpense,
  onDeleteDirectExpense,
}: {
  friend: FriendSummary | null;
  groups: GroupData[] | undefined;
  myUid: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSettleUp: (currency: string, scopeId?: string, scopeNetUnits?: number) => void;
  onAddDirectExpense: () => void;
  onEditDirectExpense?: (expense: ExpenseRow) => void;
  onDeleteDirectExpense?: (expenseId: string) => void;
}) {
  const [scopeFilter, setScopeFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<"all" | "expenses" | "settlements">("all");

  const [currencyFilter, setCurrencyFilter] = useState("all");
  useEffect(() => {
    if (open) {
      setScopeFilter("all");
      setTypeFilter("all");
      setCurrencyFilter("all");
    }
  }, [open, friend?.friendUser.id]);

  // Extract shared groups with this friend
  const sharedGroups = useMemo(() => {
    if (!friend || !groups) return [];
    const friendUid = friend.friendUser.id;
    return groups
      .filter((g) => g.members.some((m) => m.user_id === friendUid))
      .map((g) => ({
        id: g.group.id,
        name: g.group.name,
        members: g.members.map((m) => ({
          id: m.id,
          user_id: m.user_id,
          name: m.name,
        })),
        expenses: g.expenses.map((expense) => ({
          ...expense,
          splits: expense.expense_splits.map((split) => ({
            ...split,
            user_id: g.members.find((member) => member.id === split.member_id)?.user_id || "",
          })),
        })),
        settlements: g.settlements,
      }));
  }, [friend, groups]);

  // Aggregate multi-currency breakdown & transactions without cross-currency netting or cross-group netting
  const breakdownData = useMemo(() => {
    if (!friend || !myUid) {
      return { breakdownsByCurrency: {}, transactions: [] };
    }
    return calculateFriendScopeBreakdown({
      myUid,
      friendUid: friend.friendUser.id,
      friendName: friend.friendUser.display_name,
      directExpenses: friend.directExpenses,
      directSettlements: friend.directSettlements,
      sharedGroups,
    });
  }, [friend, myUid, sharedGroups]);

  const { breakdownsByCurrency, transactions } = breakdownData;
  const currencies = Object.keys(breakdownsByCurrency);

  // Filter transactions according to selected scope and type
  const filteredTransactions = useMemo(() => {
    return filterTransactionsByScope(transactions, scopeFilter, typeFilter).filter(
      (transaction) => currencyFilter === "all" || transaction.currency === currencyFilter,
    );
  }, [transactions, scopeFilter, typeFilter, currencyFilter]);

  if (!friend) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden sm:rounded-2xl">
        {/* Header */}
        <div className="p-5 border-b bg-muted/20 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <MemberAvatar
              name={friend.friendUser.display_name}
              src={friend.friendUser.avatar_url}
              className="h-12 w-12 text-base font-bold"
            />
            <div>
              <DialogTitle className="text-lg font-bold text-foreground">
                {friend.friendUser.display_name}
              </DialogTitle>
              <p className="text-xs text-muted-foreground">{friend.friendUser.email || "Friend"}</p>
              <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1 font-medium">
                  <User className="h-3 w-3 text-primary" />
                  {friend.directExpenses.length} direct expense
                  {friend.directExpenses.length !== 1 ? "s" : ""}
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1 font-medium">
                  <Users className="h-3 w-3 text-primary" />
                  {sharedGroups.length} shared group
                  {sharedGroups.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              className="h-8 text-xs"
              onClick={() =>
                onSettleUp(
                  currencies[0] || "AED",
                  "direct",
                  breakdownsByCurrency[currencies[0] || "AED"]?.scopes.find(
                    (scope) => scope.isDirect,
                  )?.netUnits || 0,
                )
              }
            >
              Record payment
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs font-medium"
              onClick={onAddDirectExpense}
            >
              <Plus className="mr-1 h-3.5 w-3.5" /> Expense
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* 1. Multi-Currency Balance Breakdowns */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Wallet className="h-3.5 w-3.5 text-primary" />
                Balance Breakdown per Currency
              </h4>
              <span className="text-[11px] text-muted-foreground">
                Payments apply to one balance
              </span>
            </div>

            {currencies.length === 0 ? (
              <div className="rounded-xl border border-dashed p-4 text-center text-xs text-muted-foreground">
                No active balances or transactions with {friend.friendUser.display_name} yet.
              </div>
            ) : (
              <div className="grid gap-3">
                {currencies.map((curr) => {
                  const b = breakdownsByCurrency[curr];
                  if (!b) return null;
                  const isSettled =
                    b.totalNetUnits === 0 && b.scopes.every((s) => s.netUnits === 0);
                  const theyOwe = b.totalNetUnits > 0;
                  const userOwes = b.totalNetUnits < 0;

                  return (
                    <div
                      key={curr}
                      className="rounded-xl border bg-card p-3.5 shadow-soft space-y-2.5 transition"
                    >
                      {/* Currency Total Summary */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-muted text-foreground">
                            {curr}
                          </span>
                          <span
                            className={`text-sm font-bold ${
                              theyOwe
                                ? "text-owed"
                                : userOwes
                                  ? "text-owe"
                                  : "text-muted-foreground"
                            }`}
                          >
                            {isSettled
                              ? "Settled up"
                              : theyOwe
                                ? `${friend.friendUser.display_name} owes you ${formatMoney(b.totalNetUnits, curr)}`
                                : userOwes
                                  ? `You owe ${friend.friendUser.display_name} ${formatMoney(Math.abs(b.totalNetUnits), curr)}`
                                  : "Balances offset — choose a balance below"}
                          </span>
                        </div>

                        {!isSettled && (
                          <Button
                            size="sm"
                            className="h-7 px-2.5 text-xs font-semibold"
                            onClick={() => {
                              const activeScope =
                                (scopeFilter !== "all" && scopeFilter !== "shared_all"
                                  ? b.scopes.find((s) => s.scopeId === scopeFilter)
                                  : undefined) ||
                                b.scopes.find((s) => s.isDirect && s.netUnits !== 0) ||
                                b.scopes.find((s) => s.netUnits !== 0) ||
                                b.scopes[0];
                              onSettleUp(curr, activeScope?.scopeId, activeScope?.netUnits);
                            }}
                          >
                            Settle Up
                          </Button>
                        )}
                      </div>

                      {/* Plain-Language Explanation */}
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {b.explanation}
                      </p>
                      <button
                        type="button"
                        className="text-xs text-primary underline"
                        onClick={() => {
                          setScopeFilter("all");
                          setCurrencyFilter(curr);
                        }}
                      >
                        View {curr} transactions
                      </button>

                      {/* Clickable Scope Breakdowns */}
                      {b.scopes.length > 0 && (
                        <div className="pt-1 flex flex-wrap gap-1.5 items-center">
                          <span className="text-[11px] text-muted-foreground mr-1">Filter by:</span>
                          {b.scopes.map((s) => {
                            const isSelected = scopeFilter === s.scopeId;
                            return (
                              <button
                                type="button"
                                key={s.scopeId}
                                onClick={() => {
                                  setScopeFilter(isSelected ? "all" : s.scopeId);
                                  setCurrencyFilter(curr);
                                }}
                                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition cursor-pointer ${
                                  isSelected
                                    ? "bg-primary text-primary-foreground border-primary"
                                    : "bg-muted/40 hover:bg-muted text-foreground border-border"
                                }`}
                              >
                                {s.isDirect ? (
                                  <User className="h-3 w-3" />
                                ) : (
                                  <Users className="h-3 w-3 text-primary" />
                                )}
                                <span>{s.scopeName}:</span>
                                <span
                                  className={`font-semibold ${
                                    isSelected
                                      ? "text-primary-foreground"
                                      : s.netUnits > 0
                                        ? "text-owed"
                                        : s.netUnits < 0
                                          ? "text-owe"
                                          : "text-muted-foreground"
                                  }`}
                                >
                                  {formatMoney(Math.abs(s.netUnits), curr)}
                                  {s.netUnits > 0
                                    ? " (owes you)"
                                    : s.netUnits < 0
                                      ? " (you owe)"
                                      : ""}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 2. Timeline Filter Chips */}
          <div className="space-y-3 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-primary" />
                Activity Timeline ({filteredTransactions.length})
              </h4>

              <label className="text-xs text-muted-foreground">
                Currency{" "}
                <select
                  aria-label="Timeline currency"
                  value={currencyFilter}
                  onChange={(event) => setCurrencyFilter(event.target.value)}
                  className="rounded border bg-background p-1"
                >
                  <option value="all">All currencies</option>
                  {currencies.map((currency) => (
                    <option key={currency} value={currency}>
                      {currency}
                    </option>
                  ))}
                </select>
              </label>
              {/* Type Filter Buttons */}
              <div className="flex items-center gap-1 bg-muted/60 p-0.5 rounded-lg border">
                <button
                  type="button"
                  onClick={() => setTypeFilter("all")}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                    typeFilter === "all"
                      ? "bg-background text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setTypeFilter("expenses")}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                    typeFilter === "expenses"
                      ? "bg-background text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Expenses
                </button>
                <button
                  type="button"
                  onClick={() => setTypeFilter("settlements")}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                    typeFilter === "settlements"
                      ? "bg-background text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Payments
                </button>
              </div>
            </div>

            {/* Scope Filter Buttons */}
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => {
                  setScopeFilter("all");
                  setCurrencyFilter("all");
                }}
                className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition ${
                  scopeFilter === "all"
                    ? "bg-primary text-primary-foreground border-primary font-semibold"
                    : "bg-background text-muted-foreground hover:bg-muted"
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setScopeFilter("direct")}
                className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition flex items-center gap-1 ${
                  scopeFilter === "direct"
                    ? "bg-primary text-primary-foreground border-primary font-semibold"
                    : "bg-background text-muted-foreground hover:bg-muted"
                }`}
              >
                <User className="h-3 w-3" /> Direct
              </button>
              <button
                type="button"
                onClick={() => setScopeFilter("shared_all")}
                className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition flex items-center gap-1 ${
                  scopeFilter === "shared_all"
                    ? "bg-primary text-primary-foreground border-primary font-semibold"
                    : "bg-background text-muted-foreground hover:bg-muted"
                }`}
              >
                <Users className="h-3 w-3" /> Shared groups
              </button>
              {sharedGroups.map((g) => (
                <button
                  type="button"
                  key={g.id}
                  onClick={() => setScopeFilter(g.id)}
                  className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition flex items-center gap-1 ${
                    scopeFilter === g.id
                      ? "bg-primary text-primary-foreground border-primary font-semibold"
                      : "bg-background text-muted-foreground hover:bg-muted"
                  }`}
                  title={g.name}
                >
                  <span className="truncate max-w-[120px]">{g.name}</span>
                </button>
              ))}
            </div>

            {/* 3. Transaction Items */}
            {filteredTransactions.length === 0 ? (
              <div className="rounded-xl border border-dashed p-6 text-center text-xs text-muted-foreground">
                No transactions match the selected filter.
              </div>
            ) : (
              <div className="divide-y rounded-xl border bg-card shadow-soft">
                {filteredTransactions.map((tx) => {
                  const rawExpense = tx.rawExpense;
                  const isExpense = tx.type === "expense";
                  const isSettlement = tx.type === "settlement";
                  const userGets = tx.netImpactForUser > 0;
                  const userOwes = tx.netImpactForUser < 0;

                  return (
                    <div
                      key={tx.id}
                      className="p-3 sm:p-4 flex items-start justify-between gap-3 hover:bg-muted/30 transition"
                    >
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        <div
                          className={`mt-0.5 rounded-full p-2 ${
                            isSettlement ? "bg-owed-soft text-owed" : "bg-primary/10 text-primary"
                          }`}
                        >
                          {isSettlement ? (
                            <CheckCircle2 className="h-4 w-4" />
                          ) : (
                            <Receipt className="h-4 w-4" />
                          )}
                        </div>

                        <div className="min-w-0 flex-1 space-y-0.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-foreground truncate">
                              {tx.description}
                            </span>
                            <span
                              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                                tx.scope === "direct"
                                  ? "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300"
                                  : "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300"
                              }`}
                            >
                              {tx.scope === "direct" ? "Direct" : tx.groupName}
                            </span>
                          </div>

                          <div className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                            <span>{tx.date}</span>
                            <span>•</span>
                            <span>Paid by {tx.paidByName}</span>
                            {tx.note && (
                              <>
                                <span>•</span>
                                <span className="italic truncate max-w-[200px]">{tx.note}</span>
                              </>
                            )}
                          </div>

                          {/* Split Details */}
                          {isExpense && (
                            <div className="text-[11px] text-muted-foreground pt-1 flex items-center gap-3">
                              <span>
                                Your share:{" "}
                                <b className="font-medium">
                                  {formatMoney(tx.userShareUnits, tx.currency)}
                                </b>
                              </span>
                              <span>
                                {friend.friendUser.display_name}'s share:{" "}
                                <b className="font-medium">
                                  {formatMoney(tx.friendShareUnits, tx.currency)}
                                </b>
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right side amount & balance impact */}
                      <div className="text-right shrink-0">
                        <div className="font-semibold text-sm text-foreground">
                          {formatMoney(tx.amountUnits, tx.currency)}
                        </div>

                        {tx.netImpactForUser !== 0 ? (
                          <div
                            className={`text-xs font-semibold flex items-center justify-end gap-0.5 ${
                              userGets ? "text-owed" : "text-owe"
                            }`}
                          >
                            {userGets ? (
                              <>
                                <ArrowDownLeft className="h-3 w-3" />+
                                {formatMoney(tx.netImpactForUser, tx.currency)}
                              </>
                            ) : (
                              <>
                                <ArrowUpRight className="h-3 w-3" />-
                                {formatMoney(Math.abs(tx.netImpactForUser), tx.currency)}
                              </>
                            )}
                          </div>
                        ) : (
                          <div className="text-[11px] text-muted-foreground">no balance change</div>
                        )}

                        {/* Direct Expense Edit link if applicable */}
                        {tx.scope === "direct" &&
                          isExpense &&
                          onEditDirectExpense &&
                          rawExpense && (
                            <button
                              type="button"
                              onClick={() => {
                                onOpenChange(false);
                                onEditDirectExpense({
                                  id: tx.id,
                                  description: rawExpense.description,
                                  amount: fromMinorUnits(
                                    rawExpense.amount_units,
                                    rawExpense.currency,
                                  ),
                                  amount_units: rawExpense.amount_units,
                                  created_by: rawExpense.created_by || null,
                                  currency: rawExpense.currency,
                                  expense_date: rawExpense.expense_date,
                                  category: rawExpense.category || "Other",
                                  paid_by_member_id: rawExpense.paid_by_uid,
                                  paid_by_uid: rawExpense.paid_by_uid,
                                  split_type: rawExpense.split_type || "EQUAL",
                                  note: rawExpense.note ?? null,
                                  expense_splits: rawExpense.splits.map((s) => ({
                                    member_id: s.user_id || s.member_id || "",
                                    amount: fromMinorUnits(s.amount_units, rawExpense.currency),
                                    amount_units: s.amount_units,
                                    percentage: s.percentage ?? null,
                                  })),
                                });
                              }}
                              className="mt-1 text-[11px] font-semibold text-primary underline"
                            >
                              Edit
                            </button>
                          )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
