import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Bell,
  BookOpen,
  Check,
  ChevronRight,
  Download,
  Filter,
  History,
  Mail,
  Pencil,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { EmptyState, MemberAvatar } from "@/components/AppShell";
import {
  CreateGroupDialog,
  AddFriendDialog,
  SendReminderDialog,
  ExportDialog,
  ExpenseDialog,
  SettleDialog,
} from "@/components/Dialogs";
import {
  errMsg,
  money,
  typeIcon,
  catIcon,
  formatDay,
  useAllGroups,
  useUser,
  useFriends,
  useRecentActivity,
  type ExpenseRow,
  type FriendSummary,
  type GroupData,
} from "@/lib/app";
import { FriendDetailDialog } from "@/components/FriendDetailDialog";
import {
  addFriendToGroup,
  deleteExpense,
  respondToFriendRequest,
  sendFriendInvitation,
} from "@/lib/fairlyshareDb";
import { formatMoney, fromMinorUnits } from "@/lib/currencies";

export const Route = createFileRoute("/_authenticated/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Fair Share" },
      {
        name: "description",
        content: "Split group and personal expenses fairly with friends, roommates, and groups.",
      },
      { property: "og:title", content: "Dashboard — Fair Share" },
      {
        property: "og:description",
        content: "Split group and personal expenses fairly with friends, roommates, and groups.",
      },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { data: me } = useUser();
  const {
    data: groups,
    isLoading: loadingGroups,
    error: errorGroups,
    refetch: refetchGroups,
  } = useAllGroups();
  const { data: friends, isLoading: loadingFriends, refetch: refetchFriends } = useFriends();
  const { data: activity, isLoading: loadingActivity } = useRecentActivity();
  const qc = useQueryClient();

  const [createGroupOpen, setCreateGroupOpen] = useState(false);
  const [addFriendOpen, setAddFriendOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  // Dialog state for Direct Expense / Settle / Reminder from People tab
  const [activeFriend, setActiveFriend] = useState<{
    id: string;
    name: string;
    friendshipId?: string;
  } | null>(null);
  const [editingDirectExpense, setEditingDirectExpense] = useState<ExpenseRow | null>(null);
  const [directExpenseOpen, setDirectExpenseOpen] = useState(false);
  const [reminderTarget, setReminderTarget] = useState<{
    uid: string;
    name: string;
    currency: string;
    amount: number;
    type: "friend" | "group";
    targetId: string;
  } | null>(null);

  // Friend Detail Ledger & Direct Settlement state
  const [friendDetailTarget, setFriendDetailTarget] = useState<FriendSummary | null>(null);
  const [friendDetailOpen, setFriendDetailOpen] = useState(false);
  const [directSettleTarget, setDirectSettleTarget] = useState<{
    friend: FriendSummary;
    currency: string;
    scopeId?: string;
    scopeNetUnits?: number;
    sharedGroups?: GroupData[];
  } | null>(null);

  // Activity filters
  const [activityFilter, setActivityFilter] = useState<string>("all");

  // Multi-currency overall totals (NO netting across currencies!)
  const totalsByCurrency: Record<string, { lent: number; borrowed: number }> = {};

  // Accumulate from groups
  for (const g of groups ?? []) {
    if (g.myMemberId) {
      for (const [c, netMap] of Object.entries(g.netByCurrency)) {
        const v = netMap[g.myMemberId] ?? 0;
        const t = (totalsByCurrency[c] ??= { lent: 0, borrowed: 0 });
        if (v > 0) t.lent += v;
        else if (v < 0) t.borrowed -= v;
      }
    }
  }

  // Accumulate from direct friends (without double-counting group expenses!)
  for (const f of friends ?? []) {
    if (f.friendship.status === "accepted") {
      for (const [c, net] of Object.entries(f.pairwiseBalances)) {
        // Pairwise balances includes direct + shared group impact
        // But to avoid double-counting group totals in top widget, direct expenses are computed:
        const directNet = f.directExpenses.reduce((sum, e) => {
          if (e.currency !== c) return sum;
          if (e.paid_by_uid === me?.id) {
            const theirShare = e.splits.find((s) => s.user_id !== me?.id)?.amount_units ?? 0;
            return sum + theirShare;
          } else {
            const myShare = e.splits.find((s) => s.user_id === me?.id)?.amount_units ?? 0;
            return sum - myShare;
          }
        }, 0);
        const directSettlementNet = f.directSettlements.reduce((sum, s) => {
          if (s.currency !== c) return sum;
          if (s.from_uid === me?.id) return sum + s.amount_units;
          return sum - s.amount_units;
        }, 0);

        const totalDirect = directNet + directSettlementNet;
        if (totalDirect !== 0) {
          const t = (totalsByCurrency[c] ??= { lent: 0, borrowed: 0 });
          if (totalDirect > 0) t.lent += totalDirect;
          else t.borrowed -= totalDirect;
        }
      }
    }
  }

  const currencies = Object.keys(totalsByCurrency);

  async function handleFriendRequest(fid: string, accept: boolean) {
    try {
      await respondToFriendRequest(fid, accept);
      toast.success(accept ? "Friend request accepted" : "Friend request declined");
      qc.invalidateQueries({ queryKey: ["friends"] });
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  const pendingRequests =
    friends?.filter(
      (f) =>
        f.friendship.status === "pending" &&
        f.friendship.sender_id !== me?.id &&
        (f.friendship.receiver_id === me?.id ||
          (f.friendship.receiver_email &&
            me?.email &&
            f.friendship.receiver_email.toLowerCase() === me.email.toLowerCase())),
    ) ?? [];

  const sentRequests =
    friends?.filter(
      (f) => f.friendship.status === "pending" && f.friendship.sender_id === me?.id,
    ) ?? [];

  const acceptedFriends = friends?.filter((f) => f.friendship.status === "accepted") ?? [];

  // Export data builder
  const allExportTransactions = (groups ?? [])
    .flatMap((g) =>
      g.expenses.map((e) => ({
        date: e.expense_date,
        type: "Expense" as const,
        description: `[${g.group.name}] ${e.description}`,
        category: e.category,
        currency: e.currency,
        amount_units: e.amount_units,
        payer: g.members.find((m) => m.id === e.paid_by_member_id)?.name || e.paid_by_uid,
        recipient_or_participants: e.expense_splits
          .map((s) => g.members.find((m) => m.id === s.member_id)?.name || s.member_id)
          .join(", "),
        my_share_or_impact: formatMoney(
          e.expense_splits.find((s) => s.member_id === g.myMemberId)?.amount_units || 0,
          e.currency,
        ),
        ...(e.note ? { note: e.note } : {}),
      })),
    )
    .concat(
      (friends ?? []).flatMap((f) =>
        f.directExpenses.map((e) => ({
          date: e.expense_date,
          type: "Expense" as const,
          description: `[Direct: ${f.friendUser.display_name}] ${e.description}`,
          category: e.category,
          currency: e.currency,
          amount_units: e.amount_units,
          payer: e.paid_by_uid === me?.id ? "You" : f.friendUser.display_name,
          recipient_or_participants: `${me?.name}, ${f.friendUser.display_name}`,
          my_share_or_impact: formatMoney(
            e.splits.find((s) => s.user_id === me?.id)?.amount_units || 0,
            e.currency,
          ),
          ...(e.note ? { note: e.note } : {}),
        })),
      ),
    );

  return (
    <div className="space-y-6">
      {/* Top Banner Greeting */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Welcome back,</p>
          <h1 className="text-2xl font-bold text-foreground">
            {me?.name?.split(" ")[0] ?? "…"} 👋
          </h1>
        </div>
        <Button variant="outline" size="sm" onClick={() => setExportOpen(true)}>
          <Download className="mr-1.5 h-3.5 w-3.5" /> Export .XLSX
        </Button>
      </div>

      {/* Multi-Currency Net Balance Card */}
      <section className="overflow-hidden rounded-3xl bg-[#17324D] p-5 text-white shadow-soft border border-[#17324D]/10">
        <div className="flex items-center justify-between">
          <p className="text-xs font-bold uppercase tracking-wider text-[#38BDF8]">Net balances</p>
        </div>
        {loadingGroups || loadingFriends ? (
          <Skeleton className="mt-3 h-10 w-48 bg-white/20" />
        ) : currencies.length === 0 ? (
          <div className="mt-3 py-1">
            <p className="font-display text-2xl font-bold text-white">All settled up ✨</p>
            <p className="text-xs text-slate-300 mt-1">
              No outstanding balances across your groups or friends.
            </p>
          </div>
        ) : (
          <div className="mt-3 space-y-4">
            {currencies.map((c) => {
              const { lent, borrowed } = totalsByCurrency[c]!;
              const net = lent - borrowed;
              return (
                <div key={c} className="border-b border-white/15 pb-4 last:border-0 last:pb-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="font-display text-xl font-bold tracking-tight">
                      {net === 0 ? (
                        <span className="text-slate-300">Settled in {c}</span>
                      ) : net > 0 ? (
                        <span className="text-emerald-400">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-300 mr-2">
                            Total owed to you:
                          </span>
                          <span className="money font-extrabold">{formatMoney(net, c)}</span>
                        </span>
                      ) : (
                        <span className="text-rose-400">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-300 mr-2">
                            Total you owe:
                          </span>
                          <span className="money font-extrabold">{formatMoney(-net, c)}</span>
                        </span>
                      )}
                    </p>
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-bold text-[#38BDF8]">
                      {c}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                    <div className="rounded-2xl bg-white p-3 text-left shadow-xs border border-slate-100">
                      <div className="flex items-center gap-1.5 text-emerald-600 mb-1">
                        <ArrowDownLeft className="h-4 w-4 shrink-0" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#17324D]">
                          You are owed
                        </span>
                      </div>
                      <div className="money text-lg font-extrabold text-emerald-600">
                        {formatMoney(lent, c)}
                      </div>
                    </div>
                    <div className="rounded-2xl bg-white p-3 text-left shadow-xs border border-slate-100">
                      <div className="flex items-center gap-1.5 text-rose-600 mb-1">
                        <ArrowUpRight className="h-4 w-4 shrink-0" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#17324D]">
                          You owe
                        </span>
                      </div>
                      <div className="money text-lg font-extrabold text-rose-600">
                        {formatMoney(borrowed, c)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Pending Friend Requests Banner */}
      {pendingRequests.length > 0 && (
        <div className="rounded-2xl border border-badge-border bg-badge p-4 space-y-3">
          <div className="flex items-center gap-2 font-semibold text-badge-foreground text-sm">
            <UserPlus className="h-4 w-4" /> Pending Friend Requests ({pendingRequests.length})
          </div>
          <div className="space-y-2">
            {pendingRequests.map((req) => (
              <div
                key={req.friendship.id}
                className="flex items-center justify-between bg-card p-3 rounded-xl border"
              >
                <div>
                  <div className="font-semibold text-sm text-foreground">
                    {req.friendUser.display_name}
                  </div>
                  <div className="text-xs text-muted-foreground">{req.friendUser.email}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    className="h-8 px-2.5"
                    onClick={() => handleFriendRequest(req.friendship.id, true)}
                  >
                    <Check className="mr-1 h-3.5 w-3.5" /> Accept
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2.5 text-muted-foreground"
                    onClick={() => handleFriendRequest(req.friendship.id, false)}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Dashboard Tabs: People | Groups | Recent Activity */}
      <Tabs defaultValue="groups" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="people">People</TabsTrigger>
          <TabsTrigger value="groups">Groups</TabsTrigger>
          <TabsTrigger value="activity">Recent Activity</TabsTrigger>
        </TabsList>

        {/* ---------------- PEOPLE TAB ---------------- */}
        <TabsContent value="people" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-foreground">Friends & People</h2>
              <p className="text-xs text-muted-foreground">
                Direct expenses and balances with friends
              </p>
            </div>
            <Button size="sm" onClick={() => setAddFriendOpen(true)}>
              <UserPlus className="mr-1.5 h-4 w-4" /> Add Friend
            </Button>
          </div>

          {sentRequests.length > 0 && (
            <div className="rounded-2xl border border-[#BAE6FD] bg-[#F0F8FF] p-3.5 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold text-[#0F2744]">
                <span className="flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5 text-[#0284C7]" />
                  Sent Email Invitations ({sentRequests.length})
                </span>
                <span className="text-[11px] font-normal text-muted-foreground">
                  Awaiting acceptance
                </span>
              </div>
              <div className="space-y-2">
                {sentRequests.map((req) => {
                  const targetMail = req.friendship.receiver_email || req.friendUser.email || "";
                  return (
                    <div
                      key={req.friendship.id}
                      className="flex items-center justify-between rounded-xl border border-[#E0EBF5] bg-card px-3 py-2"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-[#0F2744]">
                          {req.friendUser.display_name}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {targetMail} · Auto-email sent
                        </div>
                      </div>
                      {targetMail && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs shrink-0"
                          onClick={async () => {
                            try {
                              await sendFriendInvitation(targetMail);
                              toast.success(
                                `Auto-generated invitation email resent from Fair Share to ${targetMail}!`,
                              );
                            } catch (err) {
                              toast.error(errMsg(err));
                            }
                          }}
                        >
                          <Send className="mr-1.5 h-3 w-3 text-[#0284C7]" />
                          Resend Auto-Email
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {loadingFriends ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-20 rounded-2xl" />
              ))}
            </div>
          ) : acceptedFriends.length === 0 ? (
            <EmptyState
              icon={UserCheck}
              title="No friends connected yet"
              text="Invite a friend by email to split personal expenses, rent, or utilities directly without needing a group."
            >
              <Button
                className="bg-[#0F2744] text-white hover:bg-[#17324D]"
                onClick={() => setAddFriendOpen(true)}
              >
                <UserPlus className="mr-2 h-4 w-4" /> Invite friend by email
              </Button>
            </EmptyState>
          ) : (
            <div className="space-y-3">
              {acceptedFriends.map((f) => {
                const nonZeroCurrs = Object.entries(f.pairwiseBalances).filter(
                  ([, net]) => net !== 0,
                );
                const isSettled = nonZeroCurrs.length === 0;

                return (
                  <div
                    key={f.friendship.id}
                    className="rounded-2xl border bg-card p-4 shadow-soft space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div
                        className="flex items-center gap-3 cursor-pointer group"
                        onClick={() => {
                          setFriendDetailTarget(f);
                          setFriendDetailOpen(true);
                        }}
                      >
                        <MemberAvatar
                          name={f.friendUser.display_name}
                          src={f.friendUser.avatar_url}
                          className="h-10 w-10 group-hover:ring-2 group-hover:ring-primary transition"
                        />
                        <div>
                          <h3 className="font-semibold text-foreground text-sm group-hover:text-primary transition flex items-center gap-1">
                            {f.friendUser.display_name}
                            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-60 group-hover:opacity-100" />
                          </h3>
                          <p className="text-xs text-muted-foreground">
                            {f.totalDirectExpensesCount} direct transaction
                            {f.totalDirectExpensesCount !== 1 ? "s" : ""}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap justify-end">
                        <Button
                          variant="secondary"
                          size="sm"
                          className="h-8 text-xs font-medium"
                          onClick={() => {
                            setFriendDetailTarget(f);
                            setFriendDetailOpen(true);
                          }}
                        >
                          <BookOpen className="mr-1 h-3.5 w-3.5" /> Ledger
                        </Button>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm" className="h-8 text-xs">
                              <Users className="mr-1 h-3.5 w-3.5 text-[#0284C7]" /> Add to Group
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-56">
                            <DropdownMenuLabel className="text-xs">
                              Add {f.friendUser.display_name} to group
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            {(groups ?? []).filter((g) => !g.group.archived_at).length === 0 ? (
                              <DropdownMenuItem onClick={() => setCreateGroupOpen(true)}>
                                <Plus className="mr-2 h-3.5 w-3.5" /> Create a new group first
                              </DropdownMenuItem>
                            ) : (
                              (groups ?? [])
                                .filter((g) => !g.group.archived_at)
                                .map((g) => {
                                  const alreadyInGroup = g.members.some(
                                    (m) => m.user_id === f.friendUser.id,
                                  );
                                  return (
                                    <DropdownMenuItem
                                      key={g.group.id}
                                      disabled={alreadyInGroup}
                                      onClick={async () => {
                                        try {
                                          const res = await addFriendToGroup(
                                            g.group.id,
                                            f.friendUser.id,
                                          );
                                          if (!res.ok) {
                                            toast.error(res.error || "Could not add to group");
                                          } else {
                                            toast.success(
                                              `Added ${f.friendUser.display_name} to "${g.group.name}"!`,
                                            );
                                            qc.invalidateQueries({ queryKey: ["groups"] });
                                            qc.invalidateQueries({
                                              queryKey: ["group", g.group.id],
                                            });
                                          }
                                        } catch (err) {
                                          toast.error(errMsg(err));
                                        }
                                      }}
                                    >
                                      <Users className="mr-2 h-3.5 w-3.5 text-[#0284C7]" />
                                      <span className="truncate flex-1">{g.group.name}</span>
                                      {alreadyInGroup && (
                                        <span className="ml-2 text-[10px] text-muted-foreground">
                                          Joined
                                        </span>
                                      )}
                                    </DropdownMenuItem>
                                  );
                                })
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>

                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs"
                          onClick={() => {
                            setEditingDirectExpense(null);
                            setActiveFriend({
                              id: f.friendUser.id,
                              name: f.friendUser.display_name,
                              friendshipId: f.friendship.id,
                            });
                            setDirectExpenseOpen(true);
                          }}
                        >
                          <Plus className="mr-1 h-3.5 w-3.5" /> Expense
                        </Button>
                      </div>
                    </div>

                    {/* Pairwise Balances by Currency */}
                    <div className="rounded-xl bg-muted/40 p-3 space-y-2">
                      {isSettled ? (
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">
                            All balances settled
                          </span>
                          <span className="font-semibold text-muted-foreground">
                            {formatMoney(0, Object.keys(f.pairwiseBalances)[0] || "AED")}
                          </span>
                        </div>
                      ) : (
                        nonZeroCurrs.map(([curr, netUnits]) => {
                          const theyOweMe = netUnits > 0;
                          return (
                            <div key={curr} className="flex items-center justify-between text-xs">
                              <span
                                className={
                                  theyOweMe ? "text-owed font-medium" : "text-owe font-medium"
                                }
                              >
                                {theyOweMe
                                  ? `${f.friendUser.display_name} owes you`
                                  : `You owe ${f.friendUser.display_name}`}
                              </span>
                              <div className="flex items-center gap-1.5">
                                <span className="money font-semibold text-sm">
                                  {formatMoney(Math.abs(netUnits), curr)}
                                </span>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-6 px-2 text-[11px] font-semibold text-foreground cursor-pointer"
                                  onClick={() => {
                                    const friendGroups = (groups ?? []).filter((g) =>
                                      g.members.some((m) => m.user_id === f.friendUser.id),
                                    );
                                    setDirectSettleTarget({
                                      friend: f,
                                      currency: curr,
                                      scopeId: "direct",
                                      scopeNetUnits: netUnits,
                                      sharedGroups: friendGroups,
                                    });
                                  }}
                                >
                                  Settle
                                </Button>
                                {theyOweMe && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 px-2 text-[11px] text-primary"
                                    onClick={() =>
                                      setReminderTarget({
                                        uid: f.friendUser.id,
                                        name: f.friendUser.display_name,
                                        currency: curr,
                                        amount: netUnits,
                                        type: "friend",
                                        targetId: f.friendship.id,
                                      })
                                    }
                                  >
                                    <Bell className="mr-1 h-3 w-3" /> Remind
                                  </Button>
                                )}
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>

                    {/* Direct Expenses List with Edit & Delete */}
                    {f.directExpenses.length > 0 && (
                      <div className="divide-y rounded-xl border bg-background/60">
                        {f.directExpenses.map((de) => {
                          const paidByMe = de.paid_by_uid === me?.id;
                          const mySplit = de.splits.find((s) => s.user_id === me?.id);
                          const rowForEdit: ExpenseRow = {
                            id: de.id,
                            description: de.description,
                            amount: fromMinorUnits(de.amount_units, de.currency),
                            amount_units: de.amount_units,
                            currency: de.currency,
                            category: de.category,
                            paid_by_member_id: de.paid_by_member_id || de.paid_by_uid,
                            paid_by_uid: de.paid_by_uid,
                            split_type: de.split_type,
                            expense_date: de.expense_date,
                            note: de.note ?? null,
                            created_by: de.created_by,
                            expense_splits: de.splits.map((s) => ({
                              member_id: s.user_id || s.member_id || "",
                              amount: fromMinorUnits(s.amount_units, de.currency),
                              amount_units: s.amount_units,
                              percentage: s.percentage ?? null,
                            })),
                          };
                          return (
                            <div
                              key={de.id}
                              className="flex items-center justify-between gap-2 px-3 py-2 text-xs"
                            >
                              <div className="min-w-0 flex-1">
                                <p className="truncate font-semibold text-foreground">
                                  {de.description}
                                </p>
                                <p className="truncate text-[11px] text-muted-foreground">
                                  {paidByMe ? "You" : f.friendUser.display_name} paid{" "}
                                  <span className="money">
                                    {formatMoney(de.amount_units, de.currency)}
                                  </span>
                                  {" · "}
                                  {formatDay(de.expense_date)}
                                  {mySplit
                                    ? ` · Your share: ${formatMoney(mySplit.amount_units, de.currency)}`
                                    : ""}
                                </p>
                              </div>
                              <div className="flex shrink-0 items-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7"
                                  title="Edit expense"
                                  onClick={() => {
                                    setActiveFriend({
                                      id: f.friendUser.id,
                                      name: f.friendUser.display_name,
                                      friendshipId: f.friendship.id,
                                    });
                                    setEditingDirectExpense(rowForEdit);
                                    setDirectExpenseOpen(true);
                                  }}
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7 text-destructive hover:text-destructive"
                                  title="Delete expense"
                                  onClick={async () => {
                                    if (!confirm("Delete this direct expense?")) return;
                                    try {
                                      await deleteExpense(de.id);
                                      toast.success("Expense deleted");
                                      await qc.invalidateQueries();
                                    } catch (err) {
                                      toast.error(errMsg(err));
                                    }
                                  }}
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={() => {
                        setFriendDetailTarget(f);
                        setFriendDetailOpen(true);
                      }}
                      className="w-full text-center text-xs text-primary font-medium hover:underline pt-1 flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <span>View friend ledger & group breakdown</span>
                      <ChevronRight className="h-3 w-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* ---------------- GROUPS TAB ---------------- */}
        <TabsContent value="groups" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground">Your Groups</h2>
            <Button size="sm" onClick={() => setCreateGroupOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" /> Create Group
            </Button>
          </div>

          {errorGroups ? (
            <EmptyState icon={RefreshCw} title="Couldn't load groups" text={errMsg(errorGroups)}>
              <Button onClick={() => refetchGroups()}>
                <RefreshCw className="mr-2 h-4 w-4" /> Try again
              </Button>
            </EmptyState>
          ) : loadingGroups ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-32 rounded-2xl" />
              ))}
            </div>
          ) : !groups?.length ? (
            <EmptyState
              icon={Users}
              title="No groups yet"
              text="Create a group for trips, flatmates, or office lunch, then invite people."
            >
              <Button onClick={() => setCreateGroupOpen(true)}>
                <Plus className="mr-2 h-4 w-4" /> Create your first group
              </Button>
            </EmptyState>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {groups.map((g) => {
                const Icon = typeIcon(g.group.category);
                const curr = g.group.currency;
                const v = g.myMemberId ? (g.net[g.myMemberId] ?? 0) : 0;

                return (
                  <Link
                    key={g.group.id}
                    to="/group/$groupId"
                    params={{ groupId: g.group.id }}
                    search={{ add: undefined }}
                    className="rounded-2xl border bg-card p-4 shadow-soft transition hover:-translate-y-0.5"
                  >
                    <div className="flex items-start gap-3">
                      <div className="rounded-xl bg-badge p-2.5 text-badge-foreground">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate font-semibold text-foreground">{g.group.name}</h3>
                        <p className="text-xs text-muted-foreground">
                          {g.group.category} · {g.members.length} members
                          {g.group.archived_at ? " · Archived" : ""}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 flex items-center justify-between">
                      <div className="flex -space-x-2">
                        {g.members.slice(0, 4).map((m) => (
                          <MemberAvatar
                            key={m.id}
                            name={m.name}
                            src={m.avatar_url}
                            className="h-7 w-7"
                          />
                        ))}
                        {g.members.length > 4 && (
                          <span className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-card bg-muted text-[10px] font-bold text-muted-foreground">
                            +{g.members.length - 4}
                          </span>
                        )}
                      </div>
                      <span
                        className={`money text-xs font-semibold ${
                          v > 0 ? "text-owed" : v < 0 ? "text-owe" : "text-muted-foreground"
                        }`}
                      >
                        {v > 0
                          ? `You are owed ${formatMoney(v, curr)}`
                          : v < 0
                            ? `You owe ${formatMoney(-v, curr)}`
                            : "Settled"}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* ---------------- ACTIVITY TAB ---------------- */}
        <TabsContent value="activity" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground">Recent Activity</h2>
            <div className="flex items-center gap-1 bg-muted rounded-lg p-1 text-xs">
              <button
                type="button"
                className={`px-2 py-1 rounded-md font-medium ${
                  activityFilter === "all"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground"
                }`}
                onClick={() => setActivityFilter("all")}
              >
                All
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md font-medium ${
                  activityFilter === "expense"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground"
                }`}
                onClick={() => setActivityFilter("expense")}
              >
                Expenses
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md font-medium ${
                  activityFilter === "settlement"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground"
                }`}
                onClick={() => setActivityFilter("settlement")}
              >
                Settlements
              </button>
            </div>
          </div>

          {loadingActivity ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 rounded-xl" />
              ))}
            </div>
          ) : !activity?.length ? (
            <EmptyState
              icon={History}
              title="No recent activity"
              text="When you add expenses, make payments, or join groups, activity will show up here."
            />
          ) : (
            <div className="divide-y rounded-2xl border bg-card shadow-soft">
              {activity
                .filter((item) => {
                  if (activityFilter === "expense") return item.action.includes("expense");
                  if (activityFilter === "settlement") return item.action.includes("settlement");
                  return true;
                })
                .map((act) => (
                  <div key={act.id} className="flex items-center justify-between p-4">
                    <div className="space-y-0.5">
                      <p className="text-sm font-semibold text-foreground">{act.description}</p>
                      <p className="text-xs text-muted-foreground">
                        By {act.actor_name} · {formatDay(act.created_at.slice(0, 10))}
                      </p>
                    </div>
                    {act.amount_units && act.currency && (
                      <span className="money font-semibold text-sm text-foreground">
                        {formatMoney(act.amount_units, act.currency)}
                      </span>
                    )}
                  </div>
                ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <CreateGroupDialog open={createGroupOpen} onOpenChange={setCreateGroupOpen} />
      <AddFriendDialog open={addFriendOpen} onOpenChange={setAddFriendOpen} />
      {activeFriend && (
        <ExpenseDialog
          directFriend={activeFriend}
          editing={editingDirectExpense}
          open={directExpenseOpen}
          onOpenChange={(o) => {
            setDirectExpenseOpen(o);
            if (!o) {
              setActiveFriend(null);
              setEditingDirectExpense(null);
            }
          }}
        />
      )}
      {reminderTarget && (
        <SendReminderDialog
          recipientUid={reminderTarget.uid}
          recipientName={reminderTarget.name}
          currency={reminderTarget.currency}
          amountUnits={reminderTarget.amount}
          targetType={reminderTarget.type}
          targetId={reminderTarget.targetId}
          open={!!reminderTarget}
          onOpenChange={(o) => !o && setReminderTarget(null)}
        />
      )}
      <ExportDialog
        title="All My Transactions"
        transactions={allExportTransactions}
        open={exportOpen}
        onOpenChange={setExportOpen}
      />
      {friendDetailTarget && (
        <FriendDetailDialog
          friend={friendDetailTarget}
          groups={groups}
          myUid={me?.id || ""}
          open={friendDetailOpen}
          onOpenChange={(o) => {
            setFriendDetailOpen(o);
            if (!o) setFriendDetailTarget(null);
          }}
          onSettleUp={(currency, scopeId, scopeNetUnits) => {
            const friendGroups = (groups ?? []).filter((g) =>
              g.members.some((m) => m.user_id === friendDetailTarget.friendUser.id),
            );
            setDirectSettleTarget({
              friend: friendDetailTarget,
              currency,
              scopeId: scopeId || "direct",
              scopeNetUnits: scopeNetUnits ?? 0,
              sharedGroups: friendGroups,
            });
          }}
          onAddDirectExpense={() => {
            setEditingDirectExpense(null);
            setActiveFriend({
              id: friendDetailTarget.friendUser.id,
              name: friendDetailTarget.friendUser.display_name,
              friendshipId: friendDetailTarget.friendship.id,
            });
            setDirectExpenseOpen(true);
          }}
          onEditDirectExpense={(exp) => {
            setActiveFriend({
              id: friendDetailTarget.friendUser.id,
              name: friendDetailTarget.friendUser.display_name,
              friendshipId: friendDetailTarget.friendship.id,
            });
            setEditingDirectExpense(exp);
            setDirectExpenseOpen(true);
          }}
        />
      )}
      {directSettleTarget && (
        <SettleDialog
          directFriend={{
            id: directSettleTarget.friend.friendUser.id,
            name: directSettleTarget.friend.friendUser.display_name,
            friendshipId: directSettleTarget.friend.friendship.id,
          }}
          sharedGroups={directSettleTarget.sharedGroups}
          prefill={{
            from:
              (directSettleTarget.scopeNetUnits ?? 0) > 0
                ? directSettleTarget.friend.friendUser.id
                : me?.id,
            to:
              (directSettleTarget.scopeNetUnits ?? 0) > 0
                ? me?.id
                : directSettleTarget.friend.friendUser.id,
            cents: Math.abs(directSettleTarget.scopeNetUnits ?? 0),
            currency: directSettleTarget.currency,
            directNetUnits: directSettleTarget.scopeNetUnits ?? 0,
            scope: directSettleTarget.scopeId || "direct",
          }}
          open={!!directSettleTarget}
          onOpenChange={(o) => {
            if (!o) setDirectSettleTarget(null);
          }}
        />
      )}
    </div>
  );
}
