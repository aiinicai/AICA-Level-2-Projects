import * as React from "react";
import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ArchiveRestore,
  ArrowRight,
  Copy,
  Download,
  Filter,
  HandCoins,
  History,
  KeyRound,
  Link2,
  Loader2,
  LogOut,
  Mail,
  MessageCircle,
  MoreVertical,
  Pencil,
  Plus,
  Receipt,
  RefreshCw,
  Scale,
  Search,
  Send,
  Share2,
  Shield,
  ShieldOff,
  Tag,
  Trash2,
  UserMinus,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  doc,
  updateDoc,
  deleteDoc,
  collection,
  onSnapshot,
  getDocs,
  query,
  where,
} from "firebase/firestore";
import { db } from "@/lib/firebase";
import {
  addFriendToGroup,
  addPlaceholderMember,
  createClaimLink,
  deleteExpense,
  deleteSettlement,
  generateToken,
  inviteMemberByEmailToGroup,
} from "@/lib/fairlyshareDb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState, MemberAvatar } from "@/components/AppShell";
import {
  ExpenseDialog,
  SettleDialog,
  ExportDialog,
  type SettlePrefill,
} from "@/components/Dialogs";
import {
  CATEGORIES,
  catIcon,
  errMsg,
  formatDay,
  typeIcon,
  useFriends,
  useGroup,
  useUser,
  type ExpenseRow,
  type SettlementRow,
} from "@/lib/app";
import { formatMoney } from "@/lib/currencies";
import { type ExportTransaction } from "@/lib/exportExcel";

export const Route = createFileRoute("/_authenticated/group/$groupId")({
  validateSearch: (s: Record<string, unknown>) => ({
    add: s["add"] === true || s["add"] === "true" ? true : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Group — Fair Share" },
      { name: "description", content: "Expenses, balances and suggested payments for your group." },
      { property: "og:title", content: "Group — Fair Share" },
      {
        property: "og:description",
        content: "Expenses, balances and suggested payments for your group.",
      },
    ],
  }),
  component: GroupPage,
});

function GroupPage() {
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  const { groupId } = Route.useParams();
  const { add } = Route.useSearch();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: user } = useUser();
  const { data: friendsList } = useFriends();
  const { data, isLoading, error, refetch, isFetching } = useGroup(groupId);

  const [expOpen, setExpOpen] = useState(false);
  const [editing, setEditing] = useState<ExpenseRow | null>(null);
  const [settleOpen, setSettleOpen] = useState(false);
  const [prefill, setPrefill] = useState<SettlePrefill | undefined>();
  const [editingSettle, setEditingSettle] = useState<SettlementRow | null>(null);
  const [exportOpen, setExportOpen] = useState(false);

  const [q, setQ] = useState("");
  const [cat, setCat] = useState<string | null>(null);
  const [payerF, setPayerF] = useState("all");
  const [fromD, setFromD] = useState("");
  const [toD, setToD] = useState("");
  const [newName, setNewName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [invitingEmail, setInvitingEmail] = useState(false);
  const [canShare, setCanShare] = useState(false);

  useEffect(() => setCanShare(typeof navigator !== "undefined" && "share" in navigator), []);

  useEffect(() => {
    if (add && data && !data.group.archived_at) {
      setEditing(null);
      setExpOpen(true);
      navigate({ to: ".", search: { add: undefined }, replace: true });
    }
  }, [add, data, navigate]);

  // Real-time updates via Firestore onSnapshot
  useEffect(() => {
    const unsubExp = onSnapshot(
      query(collection(db, "expenses"), where("group_id", "==", groupId)),
      () => {
        qc.invalidateQueries({ queryKey: ["group", groupId] });
      },
      () => {
        // Ignore transient permission errors during initial group load
      },
    );
    const unsubSet = onSnapshot(
      query(collection(db, "settlements"), where("group_id", "==", groupId)),
      () => {
        qc.invalidateQueries({ queryKey: ["group", groupId] });
      },
      () => {
        // Ignore transient permission errors during initial group load
      },
    );
    const unsubMem = onSnapshot(
      collection(db, "groups", groupId, "members"),
      () => {
        qc.invalidateQueries({ queryKey: ["group", groupId] });
      },
      () => {
        // Ignore transient permission errors during initial group load
      },
    );
    return () => {
      unsubExp();
      unsubSet();
      unsubMem();
    };
  }, [groupId, qc]);

  if (isLoading)
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 rounded-3xl" />
        <Skeleton className="h-10" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    );

  if (error)
    return (
      <EmptyState icon={RefreshCw} title="Couldn't load this group" text={errMsg(error)}>
        <Button onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Try again
        </Button>
      </EmptyState>
    );

  if (!data)
    return (
      <EmptyState
        icon={Users}
        title="Group not found"
        text="It may have been deleted, or you're no longer a member."
      >
        <Button onClick={() => navigate({ to: "/" })}>Back to home</Button>
      </EmptyState>
    );

  const {
    group,
    members,
    expenses,
    settlements,
    net,
    netByCurrency,
    transfers,
    transfersByCurrency,
    myMemberId,
  } = data;
  const archived = !!group.archived_at;
  const nameOf = (id: string) => members.find((m) => m.id === id)?.name ?? "Someone";
  const me = members.find((m) => m.id === myMemberId);
  const isAdmin = me?.role === "admin";
  const canManage = (_createdBy?: string | null) => !archived;
  const cur = group.currency;
  const link = mounted ? `${window.location.origin}/join/${group.invite_code}` : "";
  const shareText = `Join "${group.name}" on Fair Share: ${link}`;
  const Icon = typeIcon(group.category);

  const maxAbs = Math.max(1, ...Object.values(net).map(Math.abs));
  const filtered = expenses.filter(
    (e) =>
      (!cat || e.category === cat) &&
      (payerF === "all" || e.paid_by_member_id === payerF) &&
      (!fromD || e.expense_date >= fromD) &&
      (!toD || e.expense_date <= toD) &&
      (e.description + " " + (e.note ?? "")).toLowerCase().includes(q.toLowerCase()),
  );
  const byDate = filtered.reduce<Record<string, ExpenseRow[]>>(
    (a, e) => ((a[e.expense_date] ??= []).push(e), a),
    {},
  );
  const filtersOn = !!(q || cat || payerF !== "all" || fromD || toD);

  const copy = async (t: string, msg: string) => {
    try {
      await navigator.clipboard.writeText(t);
      toast.success(msg);
    } catch {
      toast.error("Couldn't copy link. Please copy manually.");
    }
  };

  const claimLink = async (memberId: string, name: string) => {
    try {
      const tok = await createClaimLink(group.id, memberId);
      await copy(
        `${link}?claim=${tok}`,
        `Personal link for ${name} copied. It works once and expires in 7 days.`,
      );
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  async function renameGroupAction() {
    const n = prompt("Rename group", group.name);
    if (!n?.trim()) return;
    try {
      await updateDoc(doc(db, "groups", group.id), {
        name: n.trim(),
        updated_at: new Date().toISOString(),
      });
      toast.success("Group renamed");
      qc.invalidateQueries();
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function resetInviteCodeAction() {
    if (!confirm("Reset the invite link? The old link will stop working.")) return;
    try {
      const newCode = generateToken(8);
      await updateDoc(doc(db, "groups", group.id), {
        invite_code: newCode,
        updated_at: new Date().toISOString(),
      });
      toast.success("New invite link created");
      qc.invalidateQueries();
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function toggleArchiveAction() {
    if (
      !confirm(
        archived
          ? "Unarchive this group?"
          : "Archive this group? History stays, but no new expenses or payments can be added.",
      )
    )
      return;
    try {
      await updateDoc(doc(db, "groups", group.id), {
        archived_at: archived ? null : new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      toast.success(archived ? "Group unarchived" : "Group archived");
      qc.invalidateQueries();
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function leaveGroupAction() {
    if (!confirm("Leave this group? Your past expenses and balance stay in the group.")) return;
    try {
      if (isAdmin) {
        const adminCount = members.filter((m) => m.role === "admin" && m.user_id).length;
        if (adminCount <= 1 && members.filter((m) => m.user_id && m.id !== myMemberId).length > 0) {
          return toast.error("You are the only admin. Make another member admin before leaving.");
        }
      }
      if (myMemberId) {
        await updateDoc(doc(db, "groups", group.id, "members", myMemberId), {
          user_id: null,
          role: "member",
        });
        await updateDoc(doc(db, "groups", group.id), {
          member_ids: (group.member_ids ?? []).filter((id: string) => id !== user?.id),
          updated_at: new Date().toISOString(),
        });
      }
      toast.success("You left the group");
      navigate({ to: "/" });
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function deleteGroupAction() {
    // Check if any currency has unsettled balances
    const hasUnsettled = Object.values(netByCurrency).some((m) =>
      Object.values(m).some((v) => v !== 0),
    );
    if (hasUnsettled) {
      return toast.error(
        "This group still has unsettled balances. Settle up or archive it instead.",
      );
    }
    if (!confirm("Delete this group and all its history? This can't be undone.")) return;
    try {
      await deleteDoc(doc(db, "groups", group.id));
      toast.success("Group deleted");
      navigate({ to: "/" });
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function setMemberRoleAction(memberId: string, role: "admin" | "member") {
    try {
      if (role === "member") {
        const adminCount = members.filter((m) => m.role === "admin" && m.user_id).length;
        if (adminCount <= 1) {
          return toast.error("A group needs at least one admin. Make someone else admin first.");
        }
      }
      await updateDoc(doc(db, "groups", group.id, "members", memberId), { role });
      toast.success(`Role updated`);
      qc.invalidateQueries();
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function removeMemberAction(member: (typeof members)[0]) {
    if (!confirm(`Remove ${member.name}? Their past financial history will remain preserved.`))
      return;
    try {
      const hasHistory =
        expenses.some(
          (e) =>
            e.paid_by_member_id === member.id ||
            e.expense_splits.some((s) => s.member_id === member.id),
        ) ||
        settlements.some((s) => s.from_member_id === member.id || s.to_member_id === member.id);

      if (hasHistory) {
        await updateDoc(doc(db, "groups", group.id, "members", member.id), {
          user_id: null,
          role: "member",
          claim_token: null,
          claim_token_expires_at: null,
        });
        toast.success(`${member.name} unlinked; financial history preserved`);
      } else {
        await deleteDoc(doc(db, "groups", group.id, "members", member.id));
        toast.success(`${member.name} removed`);
      }
      if (member.user_id) {
        await updateDoc(doc(db, "groups", group.id), {
          member_ids: (group.member_ids ?? []).filter((id) => id !== member.user_id),
          updated_at: new Date().toISOString(),
        });
      }
      qc.invalidateQueries();
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  const exportTransactions: ExportTransaction[] = expenses
    .map((e) => ({
      date: e.expense_date,
      type: "Expense" as const,
      description: e.description,
      category: e.category,
      currency: e.currency,
      amount_units: e.amount_units,
      payer: nameOf(e.paid_by_member_id),
      recipient_or_participants: e.expense_splits.map((s) => nameOf(s.member_id)).join(", "),
      my_share_or_impact: formatMoney(
        e.expense_splits.find((s) => s.member_id === myMemberId)?.amount_units || 0,
        e.currency,
      ),
      note: e.note ?? undefined,
    }))
    .concat(
      settlements.map((s) => ({
        date: s.settled_on,
        type: "Settlement" as const,
        description: `Payment from ${nameOf(s.from_member_id)} to ${nameOf(s.to_member_id)}`,
        currency: s.currency,
        amount_units: s.amount_units,
        payer: nameOf(s.from_member_id),
        recipient_or_participants: nameOf(s.to_member_id),
        my_share_or_impact: formatMoney(s.amount_units, s.currency),
        note: s.note ?? undefined,
      })),
    );

  return (
    <div className="space-y-5">
      {archived && (
        <div className="flex items-center gap-2 rounded-2xl border border-badge-border bg-badge px-4 py-3 text-sm text-badge-foreground">
          <Archive className="h-4 w-4 shrink-0" />
          <span className="flex-1">
            This group is archived. History is kept, but no changes can be made.
          </span>
          {isAdmin && (
            <Button size="sm" variant="outline" onClick={toggleArchiveAction}>
              Unarchive
            </Button>
          )}
        </div>
      )}

      {/* Group Header Card (Navy Blue & Light Blue Contrast Theme) */}
      <section className="rounded-3xl border border-[#0F2744]/15 bg-[#0F2744] p-5 text-white shadow-soft">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-[#38BDF8]/20 p-3 text-[#38BDF8] ring-1 ring-[#38BDF8]/30">
            <Icon className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-xl font-bold text-white">{group.name}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-300">
              <span className="font-semibold text-[#38BDF8]">{group.category}</span>
              <span aria-hidden="true">·</span>
              <span>{members.length} members</span>
              <span aria-hidden="true">·</span>
              <button
                onClick={() => copy(group.invite_code, "Invite code copied")}
                className="inline-flex items-center gap-1 rounded-md border border-white/15 bg-white/10 px-2 py-0.5 font-mono text-xs text-white hover:bg-white/20 transition-colors"
              >
                <Copy className="h-3 w-3 text-[#38BDF8]" />
                {group.invite_code}
              </button>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="text-slate-200 hover:bg-white/10 hover:text-white"
              onClick={() => setExportOpen(true)}
              title="Export group transactions"
            >
              <Download className="h-4 w-4" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-slate-200 hover:bg-white/10 hover:text-white"
                  aria-label="Group options"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {isAdmin && !archived && (
                  <DropdownMenuItem onClick={renameGroupAction}>
                    <Pencil className="mr-2 h-4 w-4" />
                    Rename
                  </DropdownMenuItem>
                )}
                {isAdmin && !archived && (
                  <DropdownMenuItem onClick={resetInviteCodeAction}>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Reset invite link
                  </DropdownMenuItem>
                )}
                {isAdmin && (
                  <DropdownMenuItem onClick={toggleArchiveAction}>
                    {archived ? (
                      <ArchiveRestore className="mr-2 h-4 w-4" />
                    ) : (
                      <Archive className="mr-2 h-4 w-4" />
                    )}
                    {archived ? "Unarchive" : "Archive"}
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={leaveGroupAction}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Leave group
                </DropdownMenuItem>
                {isAdmin && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={deleteGroupAction} className="text-destructive">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete group
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        {!archived && (
          <div className="mt-4 grid grid-cols-2 gap-2.5">
            <Button
              className="bg-[#38BDF8] text-[#0F2744] hover:bg-[#7DD3FC] font-bold shadow-xs"
              onClick={() => {
                setEditing(null);
                setExpOpen(true);
              }}
            >
              <Plus className="mr-1.5 h-4 w-4" />
              Add Expense
            </Button>
            <Button
              variant="outline"
              className="border-white/25 bg-white/10 text-white hover:bg-white/20 hover:text-white font-semibold"
              onClick={() => {
                setPrefill(undefined);
                setEditingSettle(null);
                setSettleOpen(true);
              }}
            >
              <HandCoins className="mr-1.5 h-4 w-4 text-[#38BDF8]" />
              Settle Up
            </Button>
          </div>
        )}
      </section>

      {/* Tabs */}
      <Tabs defaultValue="expenses">
        <TabsList className="flex h-auto w-full justify-start overflow-x-auto">
          <TabsTrigger value="expenses">Expenses</TabsTrigger>
          <TabsTrigger value="balances">Balances</TabsTrigger>
          <TabsTrigger value="payments">Suggested</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
        </TabsList>

        {/* Expenses Tab */}
        <TabsContent value="expenses" className="space-y-3.5">
          {/* Search & Filter Bar */}
          <div className="rounded-2xl border border-[#BAE6FD] bg-[#F5FAFF] p-3 shadow-xs space-y-2.5">
            <div className="flex flex-col sm:flex-row gap-2">
              {/* Search by description or note */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="bg-card pl-9 pr-8 text-sm border-border focus-visible:ring-1 focus-visible:ring-[#38BDF8]"
                  placeholder="Search by description or note..."
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
                {q && (
                  <button
                    onClick={() => setQ("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                    title="Clear search"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Category Dropdown (mobile/compact selector) */}
              <div className="w-full sm:w-48">
                <Select value={cat ?? "all"} onValueChange={(v) => setCat(v === "all" ? null : v)}>
                  <SelectTrigger className="bg-card text-xs border-border">
                    <span className="flex items-center gap-1.5 truncate">
                      <Tag className="h-3.5 w-3.5 text-[#38BDF8]" />
                      <SelectValue placeholder="All Categories" />
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {CATEGORIES.map((c) => {
                      const CI = catIcon(c.name);
                      return (
                        <SelectItem key={c.name} value={c.name}>
                          <span className="flex items-center gap-2">
                            <CI className="h-3.5 w-3.5 text-muted-foreground" />
                            {c.name}
                          </span>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Category Interactive Filter Controls */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
              <span className="text-xs font-semibold text-[#0F2744] shrink-0 pr-1">
                Filter category:
              </span>
              {[{ name: "All" }, ...CATEGORIES].map((c) => {
                const on = (c.name === "All" && !cat) || cat === c.name;
                const CI = c.name === "All" ? Filter : catIcon(c.name);
                const count =
                  c.name === "All"
                    ? expenses.length
                    : expenses.filter((e) => e.category === c.name).length;
                return (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => setCat(c.name === "All" ? null : c.name)}
                    className={`inline-flex items-center gap-1.5 shrink-0 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors whitespace-nowrap ${
                      on
                        ? "border-[#0F2744] bg-[#0F2744] text-white shadow-xs"
                        : "border-[#BAE6FD] bg-white text-[#0F2744] hover:bg-[#E0F2FE]"
                    }`}
                  >
                    <CI className={`h-3.5 w-3.5 ${on ? "text-[#38BDF8]" : "text-[#0284C7]"}`} />
                    <span>{c.name}</span>
                    {count > 0 && (
                      <span
                        className={`money text-[11px] ${
                          on ? "text-[#38BDF8]" : "text-muted-foreground"
                        }`}
                      >
                        ({count})
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Secondary Payer & Date Filters */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 border-t border-[#E0EBF5]">
              <Select value={payerF} onValueChange={setPayerF}>
                <SelectTrigger className="bg-card text-xs">
                  <SelectValue placeholder="Anyone paid" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Anyone paid</SelectItem>
                  {members.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name} paid
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                type="date"
                aria-label="From date"
                className="bg-card text-xs"
                value={fromD}
                onChange={(e) => setFromD(e.target.value)}
              />
              <Input
                type="date"
                aria-label="To date"
                className="bg-card text-xs"
                value={toD}
                onChange={(e) => setToD(e.target.value)}
              />
            </div>

            {/* Active Filters Summary Bar */}
            {filtersOn && (
              <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
                <span className="font-medium text-[#0F2744]">
                  Showing {filtered.length} of {expenses.length} expenses
                  {cat && <span className="ml-1 text-[#38BDF8] font-bold">in {cat}</span>}
                </span>
                <button
                  onClick={() => {
                    setQ("");
                    setCat(null);
                    setPayerF("all");
                    setFromD("");
                    setToD("");
                  }}
                  className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold text-destructive hover:bg-destructive/10 transition-colors"
                >
                  <X className="h-3 w-3" />
                  Reset filters
                </button>
              </div>
            )}
          </div>

          {!filtered.length ? (
            <EmptyState
              icon={Receipt}
              title={expenses.length ? "No matches" : "No expenses yet"}
              text={
                expenses.length
                  ? "Try a different search, payer, date or category."
                  : "Add the first shared expense for this group."
              }
            >
              {filtersOn && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setQ("");
                    setCat(null);
                    setPayerF("all");
                    setFromD("");
                    setToD("");
                  }}
                >
                  Clear filters
                </Button>
              )}
            </EmptyState>
          ) : (
            Object.entries(byDate).map(([d, list]) => (
              <div key={d}>
                <p className="mb-1.5 px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {formatDay(d)}
                </p>
                <div className="divide-y rounded-2xl border bg-card shadow-soft">
                  {list.map((e) => {
                    const CI = catIcon(e.category);
                    const mine = e.expense_splits.find((s) => s.member_id === myMemberId);
                    const can = canManage(e.created_by);
                    return (
                      <div key={e.id} className="flex items-center gap-3 p-3">
                        <div className="rounded-xl bg-badge p-2 text-badge-foreground">
                          <CI className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-foreground">
                            {e.description}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            <span className="font-medium text-[#0284C7]">{e.category}</span>
                            <span className="mx-1.5" aria-hidden="true">
                              ·
                            </span>
                            {nameOf(e.paid_by_member_id)} paid{" "}
                            <span className="money">{formatMoney(e.amount_units, e.currency)}</span>
                          </p>
                          {e.note && (
                            <p className="truncate text-xs italic text-muted-foreground">
                              {e.note}
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] text-muted-foreground">your share</p>
                          <p className="money text-sm font-semibold text-foreground">
                            {mine ? formatMoney(mine.amount_units, e.currency) : "—"}
                          </p>
                        </div>
                        {can ? (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                aria-label="Expense options"
                              >
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => {
                                  setEditing(e);
                                  setExpOpen(true);
                                }}
                              >
                                <Pencil className="mr-2 h-4 w-4" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={async () => {
                                  if (!confirm("Delete this expense?")) return;
                                  try {
                                    await deleteExpense(e.id);
                                    toast.success("Expense deleted");
                                    qc.invalidateQueries();
                                  } catch (err) {
                                    toast.error(errMsg(err));
                                  }
                                }}
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        ) : (
                          <span className="w-8" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </TabsContent>

        {/* Balances Tab */}
        <TabsContent value="balances" className="space-y-4">
          {Object.entries(netByCurrency).map(([c, netMap]) => {
            const maxAbsCurr = Math.max(1, ...Object.values(netMap).map(Math.abs));
            return (
              <div key={c} className="rounded-2xl border bg-card p-4 shadow-soft space-y-3">
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Balances in {c}
                  </span>
                </div>
                {members.map((m) => {
                  const v = netMap[m.id] ?? 0;
                  const w = (Math.abs(v) / maxAbsCurr) * 50;
                  return (
                    <div key={m.id}>
                      <div className="mb-1 flex justify-between text-sm">
                        <span className="font-medium text-foreground">
                          {m.name}
                          {m.id === myMemberId && " (you)"}
                        </span>
                        <span
                          className={`money font-semibold text-xs flex items-center gap-1.5 ${
                            v > 0 ? "text-owed" : v < 0 ? "text-owe" : "text-muted-foreground"
                          }`}
                        >
                          <span className="text-[11px] font-normal text-muted-foreground">
                            {m.id === myMemberId
                              ? v > 0
                                ? "you are owed"
                                : v < 0
                                  ? "you owe"
                                  : "settled"
                              : v > 0
                                ? "is owed"
                                : v < 0
                                  ? "owes"
                                  : "settled"}
                          </span>
                          <span className="font-bold text-sm">
                            {formatMoney(Math.abs(v), c)}
                          </span>
                        </span>
                      </div>
                      <div className="relative h-2.5 rounded-full bg-muted">
                        <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                        {v !== 0 && (
                          <div
                            className={`absolute inset-y-0 rounded-full ${
                              v > 0 ? "left-1/2 bg-owed" : "right-1/2 bg-owe"
                            }`}
                            style={{ width: `${w}%` }}
                          />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </TabsContent>

        {/* Suggested Payments Tab */}
        <TabsContent value="payments" className="space-y-4">
          {Object.entries(transfersByCurrency).every(([, tList]) => tList.length === 0) ? (
            <EmptyState
              icon={Scale}
              title="All settled up"
              text="Nobody owes anything across any currency right now."
            />
          ) : (
            Object.entries(transfersByCurrency).map(([c, tList]) => (
              <div key={c} className="space-y-2">
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground px-1">
                  Settlements in {c}
                </p>
                {tList.length === 0 ? (
                  <div className="rounded-xl border bg-card p-3 text-xs text-muted-foreground">
                    All settled in {c}
                  </div>
                ) : (
                  tList.map((t, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 rounded-2xl border bg-card p-4 shadow-soft"
                    >
                      <div className="flex min-w-0 flex-1 items-center gap-2 text-sm font-semibold text-foreground">
                        <span className="truncate">{nameOf(t.from)}</span>
                        <ArrowRight className="h-4 w-4 shrink-0 text-primary" />
                        <span className="truncate">{nameOf(t.to)}</span>
                      </div>
                      <span className="money rounded-full bg-badge px-2.5 py-1 text-sm font-bold text-badge-foreground">
                        {formatMoney(t.cents, c)}
                      </span>
                      {!archived && (
                        <Button
                          size="sm"
                          onClick={() => {
                            setEditingSettle(null);
                            setPrefill({ from: t.from, to: t.to, cents: t.cents, currency: c });
                            setSettleOpen(true);
                          }}
                        >
                          Settle
                        </Button>
                      )}
                    </div>
                  ))
                )}
              </div>
            ))
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-2">
          {!settlements.length ? (
            <EmptyState
              icon={History}
              title="No payments yet"
              text="Recorded settlements will show up here."
            />
          ) : (
            settlements.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-3 rounded-2xl border bg-card p-4 shadow-soft"
              >
                <div className="rounded-xl bg-owed-soft p-2 text-owed">
                  <HandCoins className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {nameOf(s.from_member_id)} paid {nameOf(s.to_member_id)}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {formatDay(s.settled_on, { day: "numeric", month: "short", year: "numeric" })}
                    {s.note ? ` · ${s.note}` : ""}
                  </p>
                </div>
                <span className="money text-sm font-semibold text-owed">
                  {formatMoney(s.amount_units, s.currency)}
                </span>
                {canManage(s.created_by) ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        aria-label="Payment options"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => {
                          setPrefill(undefined);
                          setEditingSettle(s);
                          setSettleOpen(true);
                        }}
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        Correct
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={async () => {
                          if (!confirm("Remove this payment? Balances will be recalculated."))
                            return;
                          try {
                            await deleteSettlement(s.id);
                            toast.success("Payment removed");
                            qc.invalidateQueries();
                          } catch (err) {
                            toast.error(errMsg(err));
                          }
                        }}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Remove
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <span className="w-8" />
                )}
              </div>
            ))
          )}
        </TabsContent>

        {/* Members Tab */}
        <TabsContent value="members" className="space-y-3">
          {!archived && (
            <div className="rounded-2xl border border-[#BAE6FD] bg-[#F0F8FF] p-4 shadow-soft space-y-3">
              <div>
                <p className="text-sm font-bold text-[#0F2744]">Invite people to group</p>
                <p className="text-xs text-muted-foreground">
                  Fair Share will send an auto-generated email invitation mentioning that{" "}
                  <b className="text-[#0F2744]">{user?.name || "you"}</b> invited them to join{" "}
                  <b className="text-[#0F2744]">{group.name}</b>.
                </p>
              </div>

              <form
                className="flex flex-col sm:flex-row gap-2"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!inviteEmail.trim() || invitingEmail) return;
                  setInvitingEmail(true);
                  try {
                    const targetEmail = inviteEmail.trim().toLowerCase();
                    const res = await inviteMemberByEmailToGroup(
                      group.id,
                      group.name,
                      group.invite_code,
                      targetEmail,
                    );
                    if (!res.ok) {
                      toast.error(res.error || "Could not invite by email");
                    } else {
                      setInviteEmail("");
                      qc.invalidateQueries({ queryKey: ["group", groupId] });
                      qc.invalidateQueries({ queryKey: ["groups"] });
                      if (res.registered) {
                        toast.success(
                          `${targetEmail} was added to "${group.name}" and sent an auto-generated email from Fair Share!`,
                        );
                      } else {
                        toast.success(
                          `Auto-generated email sent from Fair Share to ${targetEmail} mentioning that ${user?.name || "you"} invited them to join "${group.name}"!`,
                        );
                      }
                    }
                  } catch (err) {
                    toast.error(errMsg(err));
                  } finally {
                    setInvitingEmail(false);
                  }
                }}
              >
                <Input
                  type="email"
                  className="bg-card flex-1 text-sm"
                  placeholder="Enter email address (e.g. friend@example.com)"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <Button
                  type="submit"
                  disabled={!inviteEmail.trim() || invitingEmail}
                  className="bg-[#0F2744] text-white hover:bg-[#17324D] shrink-0"
                >
                  {invitingEmail ? (
                    <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  ) : (
                    <Mail className="mr-1.5 h-4 w-4 text-[#38BDF8]" />
                  )}
                  Send Auto-Email Invite
                </Button>
              </form>

              {/* Quick Add from Connected Friends List */}
              {(() => {
                const availableFriends = (friendsList ?? []).filter(
                  (f) =>
                    f.friendship.status === "accepted" &&
                    !members.some((m) => m.user_id === f.friendUser.id),
                );
                if (availableFriends.length === 0) return null;
                return (
                  <div className="rounded-xl border border-[#BAE6FD] bg-card p-3 space-y-2">
                    <p className="text-xs font-bold text-[#0F2744] flex items-center gap-1.5">
                      <Users className="h-3.5 w-3.5 text-[#0284C7]" />
                      Add from Your Connected Friends
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {availableFriends.map((f) => (
                        <Button
                          key={f.friendship.id}
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs gap-1.5 border-[#BAE6FD] bg-[#F5FAFF] hover:bg-[#E0F2FE] text-[#0F2744]"
                          onClick={async () => {
                            try {
                              const res = await addFriendToGroup(group.id, f.friendUser.id);
                              if (!res.ok) {
                                toast.error(res.error || "Could not add friend to group");
                              } else {
                                toast.success(
                                  `Added ${f.friendUser.display_name} to "${group.name}"!`,
                                );
                                qc.invalidateQueries({ queryKey: ["group", groupId] });
                                qc.invalidateQueries({ queryKey: ["groups"] });
                              }
                            } catch (err) {
                              toast.error(errMsg(err));
                            }
                          }}
                        >
                          <UserPlus className="h-3.5 w-3.5 text-[#0284C7]" />
                          {f.friendUser.display_name}
                        </Button>
                      ))}
                    </div>
                  </div>
                );
              })()}

              <div className="flex flex-wrap gap-2 pt-1">
                <Button variant="outline" size="sm" className="bg-card" asChild>
                  <a
                    href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <MessageCircle className="mr-1.5 h-4 w-4 text-[#0284C7]" />
                    WhatsApp
                  </a>
                </Button>
                {canShare && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-card"
                    onClick={() =>
                      navigator
                        .share({ title: group.name, text: shareText, url: link })
                        .catch(() => {})
                    }
                  >
                    <Share2 className="mr-1.5 h-4 w-4 text-[#0284C7]" />
                    Share
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="bg-card"
                  onClick={() => copy(link, "Invite link copied")}
                >
                  <Copy className="mr-1.5 h-4 w-4 text-[#0284C7]" />
                  Copy link
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                The group link adds people as new members. To let someone take over a placeholder
                name you added, click “Personal link” next to that name.
              </p>
            </div>
          )}

          <div className="divide-y rounded-2xl border bg-card shadow-soft">
            {members.map((m) => (
              <div key={m.id} className="flex items-center gap-3 p-3">
                <MemberAvatar name={m.name} src={m.avatar_url} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {m.name}
                    {m.id === myMemberId && " (you)"}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {m.user_id ? (m.email ?? "Member") : "Placeholder (Not joined yet)"}
                  </p>
                </div>
                {m.role === "admin" && (
                  <span className="rounded-full border border-badge-border bg-badge px-2 py-0.5 text-[10px] font-semibold text-badge-foreground">
                    Admin
                  </span>
                )}
                {isAdmin && !archived && m.id !== myMemberId ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        aria-label={`Options for ${m.name}`}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {!m.user_id && (
                        <DropdownMenuItem onClick={() => claimLink(m.id, m.name)}>
                          <Link2 className="mr-2 h-4 w-4" />
                          Personal link
                        </DropdownMenuItem>
                      )}
                      {m.user_id && m.role !== "admin" && (
                        <DropdownMenuItem onClick={() => setMemberRoleAction(m.id, "admin")}>
                          <Shield className="mr-2 h-4 w-4" />
                          Make admin
                        </DropdownMenuItem>
                      )}
                      {m.user_id && m.role === "admin" && (
                        <DropdownMenuItem onClick={() => setMemberRoleAction(m.id, "member")}>
                          <ShieldOff className="mr-2 h-4 w-4" />
                          Remove admin
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => removeMemberAction(m)}
                      >
                        <UserMinus className="mr-2 h-4 w-4" />
                        Remove
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <span className="w-8" />
                )}
              </div>
            ))}
          </div>

          {isAdmin && !archived && (
            <form
              className="flex gap-2"
              onSubmit={async (e) => {
                e.preventDefault();
                if (!newName.trim()) return;
                try {
                  await addPlaceholderMember(group.id, newName.trim());
                  toast.success("Placeholder member added");
                  setNewName("");
                  qc.invalidateQueries();
                } catch (err) {
                  toast.error(errMsg(err));
                }
              }}
            >
              <Input
                className="bg-card"
                placeholder="Add placeholder member by name"
                maxLength={80}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <Button type="submit" disabled={!newName.trim()}>
                <UserPlus className="mr-1.5 h-4 w-4" />
                Add
              </Button>
            </form>
          )}

          {!isAdmin && (
            <p className="flex items-center gap-1.5 px-1 text-xs text-muted-foreground">
              <KeyRound className="h-3.5 w-3.5" />
              Only admins can add, remove or promote members.
            </p>
          )}
        </TabsContent>
      </Tabs>

      <ExpenseDialog data={data} open={expOpen} onOpenChange={setExpOpen} editing={editing} />
      <SettleDialog
        data={data}
        open={settleOpen}
        onOpenChange={setSettleOpen}
        prefill={prefill}
        editing={editingSettle}
      />
      <ExportDialog
        title={`${group.name} Transactions`}
        transactions={exportTransactions}
        open={exportOpen}
        onOpenChange={setExportOpen}
      />
    </div>
  );
}
