import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Plus,
  CheckCircle2,
  Copy,
  Download,
  Info,
  Loader2,
  Mail,
  MessageCircle,
  RefreshCw,
  Send,
  Share2,
} from "lucide-react";
import { toast } from "sonner";
import { doc, getDoc } from "firebase/firestore";
import { db } from "@/lib/firebase";
import {
  createGroup,
  ensureFriendInviteRecord,
  inviteMemberByEmailToGroup,
  saveExpense,
  saveSettlement,
  sendFriendInvitation,
  sendBalanceReminder,
  type GroupDoc,
} from "@/lib/fairlyshareDb";
import {
  toMinorUnits,
  fromMinorUnits,
  formatMoney,
  SUPPORTED_CURRENCIES,
  DEFAULT_CURRENCY,
} from "@/lib/currencies";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CATEGORIES,
  CURRENCIES,
  GROUP_TYPES,
  errMsg,
  money,
  today,
  useFriends,
  useUser,
  type ExpenseRow,
  type GroupData,
  type SettlementRow,
} from "@/lib/app";
import {
  calculatePairwiseBalances,
  splitEqual,
  splitExact,
  splitPercentage,
  calculateResultingBalance,
  generatePreSaveSplitSummary,
} from "@/lib/balanceEngine";
import { exportTransactionsToXlsx, type ExportTransaction } from "@/lib/exportExcel";

const pick = (on: boolean) =>
  `flex min-w-0 overflow-hidden flex-col items-center justify-center gap-1 rounded-xl border px-2 py-2 text-[11px] font-medium transition ${
    on
      ? "border-[#38BDF8] bg-[#E0F2FE] text-[#17324D] font-bold shadow-xs"
      : "bg-card text-muted-foreground border-border hover:bg-muted/40"
  }`;

// -------------------------------------------------------------
// CREATE GROUP DIALOG
// -------------------------------------------------------------

export function CreateGroupDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState("Trip");
  const [currency, setCurrency] = useState("AED");
  const [selectedFriends, setSelectedFriends] = useState<Set<string>>(new Set());
  const [inviteEmail, setInviteEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: friends } = useFriends();

  const acceptedFriends = useMemo(
    () => (friends ?? []).filter((f) => f.friendship.status === "accepted"),
    [friends],
  );

  useEffect(() => {
    if (!open) {
      setSelectedFriends(new Set());
      setInviteEmail("");
    }
  }, [open]);

  async function submit() {
    setBusy(true);
    try {
      const friendUids = Array.from(selectedFriends);
      const gid = await createGroup(name.trim(), type, currency, friendUids);

      if (inviteEmail.trim() && /^\S+@\S+\.\S+$/.test(inviteEmail.trim())) {
        try {
          const gSnap = await getDoc(doc(db, "groups", gid));
          const invCode = gSnap.exists() ? (gSnap.data() as GroupDoc).invite_code : "";
          await inviteMemberByEmailToGroup(gid, name.trim(), invCode, inviteEmail.trim());
        } catch {
          // Non-fatal if optional email invite encounters an issue
        }
      }

      await qc.invalidateQueries({ queryKey: ["groups"] });
      await qc.invalidateQueries({ queryKey: ["group", gid] });
      toast.success("Group created");
      onOpenChange(false);
      setName("");
      setSelectedFriends(new Set());
      setInviteEmail("");
      navigate({
        to: "/group/$groupId",
        params: { groupId: gid },
        search: { add: undefined },
      });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create group</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Vacation in Tokyo"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Type</Label>
            <div className="grid grid-cols-5 gap-2">
              {GROUP_TYPES.map(({ name: n, icon: I }) => (
                <button
                  type="button"
                  key={n}
                  onClick={() => setType(n)}
                  className={pick(type === n)}
                >
                  <I className="h-5 w-5 shrink-0" />
                  <span className="w-full truncate text-center">{n}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Default Currency</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c} — {SUPPORTED_CURRENCIES[c]?.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {acceptedFriends.length > 0 && (
            <div className="space-y-1.5">
              <Label>Add Friends to Group (optional)</Label>
              <div className="divide-y rounded-xl border max-h-36 overflow-y-auto">
                {acceptedFriends.map((f) => {
                  const fid = f.friendUser.id;
                  const checked = selectedFriends.has(fid);
                  return (
                    <label
                      key={f.friendship.id}
                      className="flex items-center gap-3 px-3 py-2 text-sm cursor-pointer hover:bg-muted/40"
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(c) =>
                          setSelectedFriends((prev) => {
                            const next = new Set(prev);
                            if (c) next.add(fid);
                            else next.delete(fid);
                            return next;
                          })
                        }
                      />
                      <span className="flex-1 truncate font-medium text-foreground">
                        {f.friendUser.display_name}
                      </span>
                      {f.friendUser.email && (
                        <span className="truncate text-xs text-muted-foreground">
                          {f.friendUser.email}
                        </span>
                      )}
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <Label>Invite Another Person by Email (optional)</Label>
            <Input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="friend@example.com"
            />
          </div>
        </div>
        <DialogFooter>
          <Button disabled={!name.trim() || busy} onClick={submit}>
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -------------------------------------------------------------
// EXPENSE DIALOG (GROUP OR DIRECT)
// -------------------------------------------------------------

type Mode = "EQUAL" | "EXACT" | "PERCENTAGE";

export function ExpenseDialog({
  data,
  directFriend,
  open,
  onOpenChange,
  editing,
}: {
  data?: GroupData;
  directFriend?: { id: string; name: string; friendshipId?: string };
  open: boolean;
  onOpenChange: (o: boolean) => void;
  editing?: ExpenseRow | null | undefined;
}) {
  const qc = useQueryClient();
  const { data: user } = useUser();
  const myUid = user?.id || "";

  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState("");
  const [curr, setCurr] = useState("AED");
  const [date, setDate] = useState("");
  const [cat, setCat] = useState("Food & Drink");
  const [payer, setPayer] = useState("");
  const [mode, setMode] = useState<Mode>("EQUAL");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [vals, setVals] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [showOptionalFields, setShowOptionalFields] = useState(false);

  const isDirect = !data && !!directFriend;
  const members = useMemo(() => {
    if (data) return data.members;
    if (directFriend && myUid) {
      return [
        {
          id: myUid,
          name: user?.name || "You",
          user_id: myUid,
          avatar_url: user?.avatar ?? null,
          role: "member" as const,
          email: user?.email ?? null,
          group_id: "",
          claim_token: null,
          claim_token_expires_at: null,
          joined_at: "",
        },
        {
          id: directFriend.id,
          name: directFriend.name,
          user_id: directFriend.id,
          avatar_url: null,
          role: "member" as const,
          email: null,
          group_id: "",
          claim_token: null,
          claim_token_expires_at: null,
          joined_at: "",
        },
      ];
    }
    return [];
  }, [data, directFriend?.id, directFriend?.name, myUid, user?.name, user?.avatar, user?.email]);

  const myMemberId = data ? data.myMemberId : myUid;

  // Initialize form only when dialog opens or when switching which expense is being edited
  const initKey = open
    ? `${editing?.id ?? "new"}_${data?.group.id ?? directFriend?.id ?? ""}_${members.length > 0 ? "ready" : "loading"}`
    : "";
  useEffect(() => {
    if (!open || members.length === 0) return;
    if (editing) {
      setNote(editing.note ?? "");
      setDesc(editing.description);
      setAmount(String(editing.amount));
      setCurr(editing.currency || data?.group.currency || "AED");
      setDate(editing.expense_date);
      setCat(editing.category);
      const resolvedPayer =
        editing.paid_by_member_id && members.some((m) => m.id === editing.paid_by_member_id)
          ? editing.paid_by_member_id
          : members.find((m) => m.user_id === editing.paid_by_uid || m.id === editing.paid_by_uid)
              ?.id ||
            myMemberId ||
            members[0]?.id ||
            "";
      setPayer(resolvedPayer);
      setMode((editing.split_type as Mode) || "EQUAL");
      const activeSplits = editing.expense_splits.filter((s) => s.amount_units > 0);
      const splitsToUse = activeSplits.length > 0 ? activeSplits : editing.expense_splits;
      setSel(
        new Set(
          splitsToUse.map(
            (s) =>
              members.find((m) => m.id === s.member_id || m.user_id === s.member_id)?.id ||
              s.member_id,
          ),
        ),
      );
      setVals(
        Object.fromEntries(
          splitsToUse.map((s) => {
            const mId =
              members.find((m) => m.id === s.member_id || m.user_id === s.member_id)?.id ||
              s.member_id;
            return [
              mId,
              String(editing.split_type === "PERCENTAGE" ? (s.percentage ?? "") : s.amount),
            ];
          }),
        ),
      );
      // Preserve existing edit values: expand optional fields if editing
      setShowOptionalFields(true);
    } else {
      let defaultCurr = data?.group.currency || "";
      if (myUid) {
        try {
          const raw = localStorage.getItem(`fairlyshare_last_prefs_${myUid}`);
          if (raw) {
            const parsed = JSON.parse(raw);
            if ((!data || parsed.groupId === data.group.id) && CURRENCIES.includes(parsed.currency))
              defaultCurr = parsed.currency;
          }
        } catch {}
      }
      if (!defaultCurr) defaultCurr = "AED";

      setNote("");
      setDesc("");
      setAmount("");
      setCurr(defaultCurr);
      setDate(today());
      setCat("Food & Drink");
      setPayer(myMemberId || members[0]?.id || "");
      setMode("EQUAL");
      setSel(new Set(members.map((m) => m.id)));
      setVals({});
      // Fast entry: keep optional fields collapsed for new expenses
      setShowOptionalFields(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initKey]);

  const rawTotal = toMinorUnits(amount || 0, curr);
  const total = Number.isFinite(rawTotal) ? rawTotal : 0;
  const pctOf = (id: string) => {
    const n = Math.round(Number(vals[id] || 0) * 100) / 100;
    return Number.isFinite(n) ? n : NaN;
  };
  const ids = members.filter((m) => sel.has(m.id)).map((m) => m.id);

  const result = useMemo(() => {
    if (total <= 0) return { ok: false as const, error: "Enter an amount" };
    if (mode === "EQUAL") return splitEqual(total, ids, payer);
    if (mode === "EXACT")
      return splitExact(
        total,
        ids.map((id) => ({ memberId: id, cents: toMinorUnits(vals[id] || 0, curr) })),
      );
    return splitPercentage(
      total,
      ids.map((id) => ({ memberId: id, pct: pctOf(id) })),
      payer,
    );
  }, [total, mode, ids.join(), vals, payer, curr]);

  const allocated =
    mode === "EXACT"
      ? ids.reduce((s, id) => s + toMinorUnits(vals[id] || 0, curr), 0)
      : mode === "PERCENTAGE"
        ? ids.reduce((s, id) => s + (pctOf(id) || 0), 0)
        : total;

  const shareOf = (id: string) =>
    result.ok ? result.shares.find((s) => s.memberId === id)?.cents : undefined;
  const valid = result.ok && desc.trim() && payer && date;

  const preSaveSummary = useMemo(() => {
    if (!result.ok || total <= 0) return null;
    return generatePreSaveSplitSummary({
      totalUnits: total,
      currency: curr,
      payerId: payer,
      myId: myMemberId || myUid,
      members: members.map((m) => ({ id: m.id, name: m.name })),
      shares: result.shares,
    });
  }, [result, total, curr, payer, myMemberId, myUid, members]);

  function selectOnlyMember(memberId: string) {
    setSel(new Set([memberId]));
    if (mode === "EXACT" && amount) {
      setVals({ [memberId]: amount });
    } else if (mode === "PERCENTAGE") {
      setVals({ [memberId]: "100" });
    }
  }

  function selectAllMembers() {
    setSel(new Set(members.map((m) => m.id)));
    setVals({});
  }

  function toggleMember(memberId: string, checked: boolean) {
    setSel((prev) => {
      const next = new Set(prev);
      if (checked) next.add(memberId);
      else next.delete(memberId);

      if (next.size === 1) {
        const soleId = Array.from(next)[0]!;
        if (mode === "EXACT" && amount) {
          setVals({ [soleId]: amount });
        } else if (mode === "PERCENTAGE") {
          setVals({ [soleId]: "100" });
        }
      }
      return next;
    });
  }

  async function save() {
    if (!result.ok) return;
    setBusy(true);
    try {
      const nonZeroShares = result.shares.filter((s) => s.cents > 0);
      const effectiveShares = nonZeroShares.length > 0 ? nonZeroShares : result.shares;

      const splits = effectiveShares.map((s) => {
        const m = members.find((mem) => mem.id === s.memberId);
        return {
          member_id: s.memberId,
          user_id: m?.user_id ?? (isDirect ? s.memberId : null),
          amount_units: s.cents,
          percentage:
            mode === "PERCENTAGE" ? (effectiveShares.length === 1 ? 100 : pctOf(s.memberId)) : null,
        };
      });

      const payerMember = members.find((m) => m.id === payer);
      const payerUid = payerMember?.user_id || (isDirect ? payer : myUid || payer);

      const participantSet = new Set<string>();
      if (myUid) participantSet.add(myUid);
      if (payerMember?.user_id) participantSet.add(payerMember.user_id);
      for (const s of splits) {
        if (s.user_id) participantSet.add(s.user_id);
      }
      if (data) {
        for (const uid of data.group.member_ids ?? []) {
          if (uid) participantSet.add(uid);
        }
        for (const m of data.members) {
          if (m.user_id) participantSet.add(m.user_id);
        }
      }
      if (isDirect && directFriend) {
        participantSet.add(directFriend.id);
      }

      const participantUids = Array.from(participantSet).filter(Boolean);

      await saveExpense({
        expenseId: editing?.id,
        groupId: data?.group.id ?? null,
        friendshipId: isDirect ? (directFriend.friendshipId ?? directFriend.id) : null,
        description: desc.trim(),
        amount_units: total,
        currency: curr,
        category: cat,
        paid_by_member_id: data ? payer : payer,
        paid_by_uid: payerUid,
        split_type: mode,
        expense_date: date,
        splits,
        note: note.trim() || null,
        participant_uids: participantUids,
      });

      toast.success(editing ? "Expense updated" : "Expense added");
      if (myUid && !editing) {
        try {
          localStorage.setItem(
            `fairlyshare_last_prefs_${myUid}`,
            JSON.stringify({
              groupId: data?.group.id || null,
              currency: curr,
            }),
          );
        } catch {
          // Ignore localStorage errors
        }
      }
      await qc.invalidateQueries();
      onOpenChange(false);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] w-[calc(100vw-1.5rem)] max-w-lg overflow-y-auto overflow-x-hidden p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit expense" : "Add expense"}</DialogTitle>
        </DialogHeader>
        <div className="min-w-0 space-y-4">
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="e.g. Team lunch, taxi, groceries"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-1.5">
              <Label>Amount</Label>
              <Input
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => {
                  const val = e.target.value;
                  setAmount(val);
                  if (mode === "EXACT" && sel.size === 1) {
                    const soleId = Array.from(sel)[0]!;
                    setVals({ [soleId]: val });
                  }
                }}
                className="money"
                placeholder="0.00"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Currency</Label>
              <Select value={curr} onValueChange={setCurr}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Date</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Paid by</Label>
              <Select value={payer} onValueChange={setPayer}>
                <SelectTrigger>
                  <SelectValue placeholder="Who paid?" />
                </SelectTrigger>
                <SelectContent>
                  {members.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name}
                      {m.id === myMemberId && !m.name.includes("(you)") ? " (you)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {!showOptionalFields && !editing ? (
            <div>
              <button
                type="button"
                onClick={() => setShowOptionalFields(true)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline py-1"
              >
                <Plus className="h-3.5 w-3.5" /> More options (Category, Note)
              </button>
            </div>
          ) : (
            <div className="space-y-3 rounded-xl border bg-muted/20 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Category & Note
                </span>
                {!editing && (
                  <button
                    type="button"
                    onClick={() => setShowOptionalFields(false)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    Hide
                  </button>
                )}
              </div>

              <div className="space-y-1.5">
                <Label>Category</Label>
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                  {CATEGORIES.map(({ name, icon: I }) => (
                    <button
                      type="button"
                      key={name}
                      onClick={() => setCat(name)}
                      className={pick(cat === name)}
                    >
                      <I className="h-4 w-4 shrink-0" />
                      <span className="w-full truncate text-center leading-tight">{name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label>Note (optional)</Label>
                <Input
                  value={note}
                  maxLength={500}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. includes tip and service fee"
                />
              </div>
            </div>
          )}

          <div className="space-y-2.5 pt-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Label className="text-sm font-semibold">Split between / For whom</Label>
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={selectAllMembers}
                  className={`rounded-md border px-2 py-1 text-xs font-medium transition ${
                    sel.size === members.length
                      ? "border-[#0F2744] bg-[#0F2744] text-white"
                      : "border-border bg-card text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  All ({members.length})
                </button>
                {myMemberId && (
                  <button
                    type="button"
                    onClick={() => selectOnlyMember(myMemberId)}
                    className={`rounded-md border px-2 py-1 text-xs font-medium transition ${
                      sel.size === 1 && sel.has(myMemberId)
                        ? "border-[#0F2744] bg-[#0F2744] text-white"
                        : "border-border bg-card text-muted-foreground hover:bg-muted/50"
                    }`}
                  >
                    Only me
                  </button>
                )}
              </div>
            </div>

            <Tabs
              value={mode}
              onValueChange={(v) => {
                const nextMode = v as Mode;
                setMode(nextMode);
                if (sel.size === 1) {
                  const soleId = Array.from(sel)[0]!;
                  if (nextMode === "EXACT" && amount) {
                    setVals({ [soleId]: amount });
                  } else if (nextMode === "PERCENTAGE") {
                    setVals({ [soleId]: "100" });
                  } else {
                    setVals({});
                  }
                } else {
                  setVals({});
                }
              }}
            >
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="EQUAL">Equal</TabsTrigger>
                <TabsTrigger value="EXACT">Exact</TabsTrigger>
                <TabsTrigger value="PERCENTAGE">Percentage</TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="divide-y rounded-xl border bg-card">
              {members.map((m) => {
                const isSelected = sel.has(m.id);
                const isOnlySelected = sel.size === 1 && isSelected;
                const memberShare = shareOf(m.id);

                return (
                  <div key={m.id} className="flex items-center justify-between gap-2 px-3 py-2.5">
                    <div
                      className="flex min-w-0 flex-1 items-center gap-2.5 cursor-pointer select-none"
                      onClick={() => toggleMember(m.id, !isSelected)}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(c) => toggleMember(m.id, !!c)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="truncate text-sm font-medium text-foreground">
                        {m.name}
                        {m.id === myMemberId && !m.name.includes("(you)") ? " (you)" : ""}
                      </span>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {members.length > 1 && (
                        <button
                          type="button"
                          onClick={() => selectOnlyMember(m.id)}
                          className={`rounded-md border px-2 py-0.5 text-[11px] font-medium transition ${
                            isOnlySelected
                              ? "border-[#38BDF8] bg-[#E0F2FE] text-[#0F2744] font-semibold"
                              : "border-border bg-muted/30 text-muted-foreground hover:bg-muted"
                          }`}
                          title={`Put 100% of this expense on ${m.name}`}
                        >
                          Only
                        </button>
                      )}

                      {mode !== "EQUAL" && isSelected && (
                        <Input
                          type="number"
                          inputMode="decimal"
                          step="0.01"
                          min="0"
                          className="money h-8 w-24 text-right text-xs"
                          placeholder={mode === "PERCENTAGE" ? "%" : "0.00"}
                          value={vals[m.id] ?? ""}
                          onChange={(e) => setVals((v) => ({ ...v, [m.id]: e.target.value }))}
                        />
                      )}

                      {mode !== "EXACT" && (
                        <span className="money w-20 text-right text-xs font-medium text-muted-foreground">
                          {isSelected && memberShare !== undefined
                            ? formatMoney(memberShare, curr)
                            : "—"}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {mode !== "EQUAL" && (
              <p className={`text-xs font-medium ${result.ok ? "text-owed" : "text-owe"}`}>
                {mode === "EXACT"
                  ? `Remaining to allocate: ${formatMoney(total - allocated, curr)}`
                  : `Remaining to allocate: ${+(100 - allocated).toFixed(2)}%`}
              </p>
            )}
            {mode === "EQUAL" && !result.ok && total > 0 && (
              <p className="text-xs font-medium text-owe">{result.error}</p>
            )}

            {preSaveSummary && (
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs text-primary font-medium flex items-start gap-2">
                <Info className="h-4 w-4 shrink-0 mt-0.5 text-primary" />
                <span className="leading-relaxed">{preSaveSummary}</span>
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button disabled={!valid || busy} onClick={save}>
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -------------------------------------------------------------
// SETTLE UP DIALOG
// -------------------------------------------------------------

export interface SettlePrefill {
  from?: string | undefined;
  to?: string | undefined;
  cents?: number | undefined;
  currency?: string | undefined;
  directNetUnits?: number | undefined;
  scope?: string | undefined;
}

export function SettleDialog({
  data,
  directFriend,
  sharedGroups,
  prefill,
  open,
  onOpenChange,
  editing,
}: {
  data?: GroupData | undefined;
  directFriend?: { id: string; name: string; friendshipId?: string } | undefined;
  sharedGroups?: GroupData[] | undefined;
  prefill?: SettlePrefill | undefined;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  editing?: SettlementRow | null | undefined;
}) {
  const qc = useQueryClient();
  const { data: settlementFriends } = useFriends();
  const settlementFriend = settlementFriends?.find(
    (f) => f.friendUser.id === directFriend?.id && f.friendship.status === "accepted",
  );
  const { data: user } = useUser();
  const myUid = user?.id || "";

  const [paymentScope, setPaymentScope] = useState<string>("direct");

  const activeGroup = useMemo(() => {
    if (data) return data;
    if (paymentScope !== "direct" && sharedGroups) {
      return sharedGroups.find((g) => g.group.id === paymentScope);
    }
    return undefined;
  }, [data, paymentScope, sharedGroups]);

  const isDirectScope = !activeGroup;

  const members = useMemo(() => {
    if (activeGroup)
      return directFriend
        ? activeGroup.members.filter((m) => m.user_id === myUid || m.user_id === directFriend.id)
        : activeGroup.members;
    if (directFriend && myUid) {
      return [
        {
          id: myUid,
          name: user?.name || "You",
          user_id: myUid,
          avatar_url: user?.avatar ?? null,
          role: "member" as const,
          email: user?.email ?? null,
          group_id: "",
          claim_token: null,
          claim_token_expires_at: null,
          joined_at: "",
        },
        {
          id: directFriend.id,
          name: directFriend.name,
          user_id: directFriend.id,
          avatar_url: null,
          role: "member" as const,
          email: null,
          group_id: "",
          claim_token: null,
          claim_token_expires_at: null,
          joined_at: "",
        },
      ];
    }
    return [];
  }, [
    activeGroup,
    directFriend?.id,
    directFriend?.name,
    myUid,
    user?.name,
    user?.avatar,
    user?.email,
  ]);

  const myMemberId = activeGroup
    ? activeGroup.myMemberId || activeGroup.members.find((m) => m.user_id === myUid)?.id || myUid
    : myUid;

  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [curr, setCurr] = useState(data?.group.currency || prefill?.currency || "AED");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (editing) {
      const scopeVal = data?.group.id || prefill?.scope || "direct";
      setPaymentScope(scopeVal);
      setFrom(editing.from_member_id || editing.from_uid);
      setTo(editing.to_member_id || editing.to_uid);
      setAmount(String(editing.amount));
      setCurr(editing.currency || data?.group.currency || "AED");
      setDate(editing.settled_on);
      setNote(editing.note ?? "");
    } else {
      const defaultScope = prefill?.scope || "direct";
      setPaymentScope(defaultScope);
      const isScopeGroup =
        defaultScope !== "direct" && sharedGroups?.some((g) => g.group.id === defaultScope);
      const currentGroup = isScopeGroup
        ? sharedGroups?.find((g) => g.group.id === defaultScope)
        : data;
      const defaultCurr =
        prefill?.currency || currentGroup?.group.currency || data?.group.currency || "AED";
      setCurr(defaultCurr);

      const resolvedMyId = currentGroup
        ? currentGroup.myMemberId ||
          currentGroup.members.find((m) => m.user_id === myUid)?.id ||
          myUid
        : myUid;
      const resolvedFriendId = currentGroup
        ? currentGroup.members.find((m) => m.user_id === directFriend?.id)?.id ||
          directFriend?.id ||
          ""
        : directFriend?.id || "";

      const resolveId = (id: string | undefined, fallback: string) =>
        currentGroup
          ? currentGroup.members.find((m) => m.id === id || m.user_id === id)?.id || fallback
          : id || fallback;
      setFrom(resolveId(prefill?.from, resolvedMyId));
      setTo(resolveId(prefill?.to, resolvedFriendId));
      setAmount(prefill?.cents ? fromMinorUnits(prefill.cents, defaultCurr).toString() : "");
      setDate(today());
      setNote("");
    }
    setOver(false);
    // Initialize only for a new dialog session; background data refreshes preserve the draft.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, editing?.id, data?.group.id, directFriend?.id, myUid]);

  const friendNetByCurrency = useMemo(() => {
    if (!directFriend || !myUid) return {} as Record<string, number>;
    if (activeGroup) {
      const uidFor = (id: string) => activeGroup.members.find((m) => m.id === id)?.user_id || id;
      return calculatePairwiseBalances(
        myUid,
        directFriend.id,
        activeGroup.expenses.map((e) => ({
          paidBy: e.paid_by_uid || uidFor(e.paid_by_member_id),
          cents: e.amount_units,
          currency: e.currency,
          shares: e.expense_splits.map((split) => ({
            memberId: uidFor(split.member_id),
            cents: split.amount_units,
          })),
        })),
        activeGroup.settlements
          .filter((payment) => payment.id !== editing?.id)
          .map((payment) => ({
            from: payment.from_uid || uidFor(payment.from_member_id),
            to: payment.to_uid || uidFor(payment.to_member_id),
            cents: payment.amount_units,
            currency: payment.currency,
          })),
      );
    }
    if (paymentScope !== "direct" || !settlementFriend) return {} as Record<string, number>;
    return calculatePairwiseBalances(
      myUid,
      directFriend.id,
      settlementFriend.directExpenses.map((e) => ({
        paidBy: e.paid_by_uid,
        cents: e.amount_units,
        currency: e.currency,
        shares: e.splits.map((split) => ({
          memberId: split.user_id || split.member_id || "",
          cents: split.amount_units,
        })),
      })),
      settlementFriend.directSettlements
        .filter((payment) => payment.id !== editing?.id)
        .map((payment) => ({
          from: payment.from_uid,
          to: payment.to_uid,
          cents: payment.amount_units,
          currency: payment.currency,
        })),
    );
  }, [activeGroup, directFriend?.id, myUid, settlementFriend, paymentScope, editing?.id]);
  const friendNet = friendNetByCurrency[curr] ?? 0;
  const scopeValid = !!data || paymentScope === "direct" || !!activeGroup;
  const fromUidForPreview = members.find((m) => m.id === from)?.user_id || from;

  const outstanding = useMemo(() => {
    if (!from || !to || from === to) return 0;
    if (directFriend)
      return fromUidForPreview === myUid ? Math.max(0, -friendNet) : Math.max(0, friendNet);
    if (activeGroup) {
      const currNet = activeGroup.netByCurrency[curr] || {};
      const adj = (id: string) => {
        let v = currNet[id] ?? 0;
        if (editing && editing.currency === curr && !!data) {
          const c = editing.amount_units;
          if (id === editing.from_member_id) v -= c;
          if (id === editing.to_member_id) v += c;
        }
        return v;
      };
      return Math.max(0, Math.min(-adj(from), adj(to)));
    }

    return 0;
  }, [
    from,
    to,
    activeGroup,
    isDirectScope,
    curr,
    editing,
    prefill?.currency,
    prefill?.directNetUnits,
    myUid,
    directFriend,
    friendNet,
    fromUidForPreview,
  ]);

  const units = toMinorUnits(amount || 0, curr);
  const finite = Number.isFinite(units) && units > 0;
  const tooMuch = finite && units > outstanding && (outstanding > 0 || !!directFriend);
  const valid =
    scopeValid &&
    (!directFriend || !!settlementFriend) &&
    members.some((m) => m.id === from) &&
    members.some((m) => m.id === to) &&
    from !== to &&
    finite &&
    !!date &&
    (!tooMuch || over);

  // Resulting balance preview using pure integer calculation
  const resultingPreview = useMemo(() => {
    if (!finite || units <= 0 || !scopeValid) return null;
    if (directFriend) {
      const result = calculateResultingBalance({
        currentNetUnits: friendNet,
        direction: fromUidForPreview === myUid ? "user_paid_friend" : "friend_paid_user",
        paymentUnits: units,
        currency: curr,
        friendName: directFriend.name,
      });
      return {
        ...result,
        label: `${result.label} · ${activeGroup ? activeGroup.group.name : "Direct"}`,
      };
    }
    if (activeGroup) {
      const map = activeGroup.netByCurrency[curr] || {};
      let before = map[myMemberId] ?? 0;
      if (editing && editing.currency === curr) {
        if (editing.from_member_id === myMemberId) before -= editing.amount_units;
        if (editing.to_member_id === myMemberId) before += editing.amount_units;
      }
      const after = before + (from === myMemberId ? units : 0) - (to === myMemberId ? units : 0);
      return {
        status: after === 0 ? ("settled" as const) : ("partial" as const),
        label:
          after === 0
            ? `Your balance in ${activeGroup.group.name} will be settled.`
            : `In ${activeGroup.group.name}, you will ${after > 0 ? "be owed" : "owe"} ${formatMoney(Math.abs(after), curr)} in total.`,
      };
    }

    return null;
  }, [
    finite,
    units,
    isDirectScope,
    activeGroup,
    directFriend,
    from,
    to,
    myMemberId,
    myUid,
    prefill?.currency,
    prefill?.directNetUnits,
    curr,
    scopeValid,
    friendNet,
    fromUidForPreview,
  ]);

  async function save() {
    if (!valid || busy) return;
    setBusy(true);
    try {
      const fromMem = members.find((m) => m.id === from);
      const toMem = members.find((m) => m.id === to);
      const fromUid = fromMem?.user_id || from;
      const toUid = toMem?.user_id || to;

      if (isDirectScope) {
        await saveSettlement({
          settlementId: editing?.id || null,
          groupId: null,
          friendshipId: directFriend?.friendshipId || null,
          from_member_id: null,
          to_member_id: null,
          from_uid: fromUid,
          to_uid: toUid,
          amount_units: units,
          currency: curr,
          settled_on: date,
          note: note.trim() || null,
        });
      } else {
        await saveSettlement({
          settlementId: editing?.id || null,
          groupId: activeGroup!.group.id,
          friendshipId: null,
          from_member_id: from,
          to_member_id: to,
          from_uid: fromUid,
          to_uid: toUid,
          amount_units: units,
          currency: curr,
          settled_on: date,
          note: note.trim() || null,
        });
      }

      toast.success(editing ? "Payment updated" : "Payment recorded");
      qc.invalidateQueries();
      onOpenChange(false);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  const sel = (v: string, set: (s: string) => void, ph: string) => (
    <Select
      value={v}
      onValueChange={(x) => {
        set(x);
        setOver(false);
      }}
    >
      <SelectTrigger>
        <SelectValue placeholder={ph} />
      </SelectTrigger>
      <SelectContent>
        {members.map((m) => (
          <SelectItem key={m.id} value={m.id}>
            {m.name}
            {m.id === myMemberId ? " (you)" : ""}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {editing
              ? "Edit payment"
              : isDirectScope && directFriend
                ? `Settle up with ${directFriend.name}`
                : activeGroup
                  ? `Record payment in ${activeGroup.group.name}`
                  : "Settle up"}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* Explicit payment scope selector when settling with friend */}
          {directFriend && !editing && (
            <div className="space-y-1.5">
              <Label>Payment Scope</Label>
              <Select
                value={paymentScope}
                onValueChange={(val) => {
                  setPaymentScope(val);
                  setAmount("");
                  setOver(false);
                  const grp =
                    val !== "direct" ? sharedGroups?.find((g) => g.group.id === val) : undefined;
                  if (grp) {
                    const mMy =
                      grp.myMemberId || grp.members.find((m) => m.user_id === myUid)?.id || myUid;
                    const mFriend =
                      grp.members.find((m) => m.user_id === directFriend.id)?.id || "";
                    setFrom(mMy);
                    setTo(mFriend);
                  } else {
                    setFrom(myUid);
                    setTo(directFriend.id);
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select payment scope" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="direct">
                    Direct (One-on-one with {directFriend.name})
                  </SelectItem>
                  {(sharedGroups ?? []).map((g) => (
                    <SelectItem key={g.group.id} value={g.group.id}>
                      Group: {g.group.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>From (Payer)</Label>
              {sel(from, setFrom, "Payer")}
            </div>
            <div className="space-y-1.5">
              <Label>To (Receiver)</Label>
              {sel(to, setTo, "Receiver")}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Currency</Label>
            <Select
              value={curr}
              onValueChange={(value) => {
                setCurr(value);
                setAmount("");
                setOver(false);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {from && to && from !== to && (
            <div className="flex items-center justify-between rounded-xl bg-badge px-3 py-2 text-xs text-badge-foreground">
              <span>
                Outstanding in {curr} (
                {isDirectScope ? "Direct" : activeGroup?.group.name || "Group"}):{" "}
                <b className="money">{formatMoney(outstanding, curr)}</b>
              </span>
              {outstanding > 0 && (
                <button
                  type="button"
                  className="font-semibold underline cursor-pointer"
                  onClick={() => setAmount(fromMinorUnits(outstanding, curr).toString())}
                >
                  Use full amount
                </button>
              )}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Amount ({curr})</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                inputMode="decimal"
                className="money"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value);
                  setOver(false);
                }}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Date</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
          </div>

          {resultingPreview && (
            <div
              className={`rounded-xl border p-3 text-xs font-medium space-y-1 ${
                resultingPreview.status === "settled"
                  ? "bg-owed-soft text-owed border-owed/20"
                  : resultingPreview.status === "overpaid"
                    ? "bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-950 dark:text-amber-200"
                    : "bg-muted/40 text-foreground border-border"
              }`}
            >
              <div className="font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Resulting Balance</span>
              </div>
              <p className="leading-relaxed">{resultingPreview.label}</p>
            </div>
          )}

          {tooMuch && (
            <label className="flex items-start gap-2 rounded-xl bg-owe-soft p-3 text-xs text-owe">
              <Checkbox checked={over} onCheckedChange={(c) => setOver(!!c)} className="mt-0.5" />
              <span>
                This exceeds the amount owed in this direction ( {formatMoney(outstanding, curr)}).
                Record it anyway (for example, an advance payment or overpayment).
              </span>
            </label>
          )}
          <div className="space-y-1.5">
            <Label>Note (optional)</Label>
            <Input
              value={note}
              maxLength={500}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Paid via UPI, Revolut, Cash"
            />
          </div>
        </div>
        <DialogFooter>
          <Button disabled={!valid || busy} onClick={save}>
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {editing ? "Save changes" : "Record payment"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -------------------------------------------------------------
// ADD FRIEND DIALOG
// -------------------------------------------------------------

export function AddFriendDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const { data: me } = useUser();
  const [emailOrCode, setEmailOrCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [invitedEmail, setInvitedEmail] = useState<string | null>(null);
  const [senderLabel, setSenderLabel] = useState<string>("You");
  const qc = useQueryClient();

  useEffect(() => {
    if (!open) {
      setInvitedEmail(null);
      setEmailOrCode("");
    } else {
      // Ensure friend invite record exists in Firestore so WhatsApp / Link invites always resolve
      ensureFriendInviteRecord().catch(() => {});
    }
  }, [open]);

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const myName = me?.name || me?.email || "A Fair Share user";
  const inviteLink = me?.id
    ? `${origin}/join/friend_${me.id}?invitedBy=${encodeURIComponent(myName)}`
    : origin;
  const shareText = `${myName} has invited you to join Fair Share to split expenses and group bills easily: ${inviteLink}`;

  async function send(e?: React.FormEvent, overrideEmail?: string) {
    if (e) e.preventDefault();
    const target = (overrideEmail ?? emailOrCode).trim();
    if (!target || busy) return;
    setBusy(true);
    try {
      const res = await sendFriendInvitation(target);
      if (!res.ok) {
        toast.error(res.error || "Could not send friend invitation");
      } else {
        qc.invalidateQueries({ queryKey: ["friends"] });
        const inviter = res.senderName || myName;
        setSenderLabel(inviter);
        setInvitedEmail(res.email || target.toLowerCase());
        toast.success(
          `Auto-generated email sent from Fair Share to ${res.email || target} mentioning that ${inviter} invited them to join Fair Share!`,
        );
      }
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  function shareInvite() {
    if (typeof navigator !== "undefined" && navigator.share) {
      navigator.share({ title: "Fair Share", text: shareText, url: inviteLink }).catch(() => {});
    } else if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(inviteLink);
      toast.success("Personal friend invite link copied to clipboard!");
    }
  }

  function copyLink() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(inviteLink);
      toast.success("Friend invite link copied! Share it anywhere to connect.");
    }
  }

  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite a Friend to Fair Share</DialogTitle>
        </DialogHeader>
        {invitedEmail ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-[#BAE6FD] bg-[#F0F8FF] p-4 space-y-2">
              <div className="flex items-center gap-2 text-[#0F2744] font-semibold text-sm">
                <CheckCircle2 className="h-4 w-4 text-[#0284C7] shrink-0" />
                Auto-Generated Email Sent to {invitedEmail}
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Fair Share has automatically sent an invitation email to{" "}
                <b className="text-foreground">{invitedEmail}</b> mentioning that{" "}
                <b className="text-foreground">{senderLabel}</b> has invited them to join Fair
                Share. Once they accept, you will both appear in each other&apos;s Friends list and
                can add each other to any group.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Button
                type="button"
                disabled={busy}
                onClick={() => send(undefined, invitedEmail)}
                className="bg-[#0F2744] text-white hover:bg-[#17324D]"
              >
                {busy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4 text-[#38BDF8]" />
                )}
                Resend Auto-Email
              </Button>
              <Button type="button" variant="outline" onClick={copyLink}>
                <Copy className="mr-2 h-4 w-4" /> Copy Friend Link
              </Button>
            </div>
            <Button variant="ghost" className="w-full text-xs" onClick={() => onOpenChange(false)}>
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={(e) => send(e)} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Enter your friend&apos;s email address and Fair Share will automatically send them an
              invitation email mentioning that <b className="text-foreground">{myName}</b> invited
              them to join Fair Share.
            </p>
            <div className="space-y-1.5">
              <Label htmlFor="friend-email-input">Friend&apos;s Email</Label>
              <Input
                id="friend-email-input"
                type="email"
                placeholder="friend@example.com"
                value={emailOrCode}
                onChange={(e) => setEmailOrCode(e.target.value)}
              />
            </div>
            <Button
              type="submit"
              disabled={!emailOrCode.trim() || busy}
              className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
            >
              {busy ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Mail className="mr-2 h-4 w-4 text-[#38BDF8]" />
              )}
              Send Auto-Email Invitation
            </Button>

            <div className="my-3 flex items-center gap-3 text-xs text-muted-foreground">
              <div className="h-px flex-1 bg-border" />
              or invite directly via link / WhatsApp
              <div className="h-px flex-1 bg-border" />
            </div>

            <div className="grid grid-cols-3 gap-2">
              <Button type="button" variant="outline" asChild className="gap-1.5 text-xs">
                <a href={whatsappUrl} target="_blank" rel="noreferrer">
                  <MessageCircle className="h-3.5 w-3.5 text-[#0284C7]" /> WhatsApp
                </a>
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={copyLink}
                className="gap-1.5 text-xs"
              >
                <Copy className="h-3.5 w-3.5 text-[#0284C7]" /> Copy Link
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={shareInvite}
                className="gap-1.5 text-xs"
              >
                <Share2 className="h-3.5 w-3.5 text-[#0284C7]" /> Share
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

// -------------------------------------------------------------
// SEND REMINDER DIALOG (RATE-LIMITED)
// -------------------------------------------------------------

export function SendReminderDialog({
  recipientUid,
  recipientName,
  currency,
  amountUnits,
  targetType,
  targetId,
  open,
  onOpenChange,
}: {
  recipientUid: string;
  recipientName: string;
  currency: string;
  amountUnits: number;
  targetType: "group" | "friend";
  targetId: string;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function handleSend() {
    setBusy(true);
    try {
      const res = await sendBalanceReminder({
        recipient_uid: recipientUid,
        currency,
        amount_units: amountUnits,
        target_type: targetType,
        target_id: targetId,
        title: `Reminder for ${formatMoney(amountUnits, currency)}`,
      });

      if (!res.ok) {
        toast.error(res.error || "Failed to send reminder");
      } else {
        toast.success(`Reminder sent to ${recipientName}!`);
        onOpenChange(false);
      }
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send Balance Reminder</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Send a friendly in-app notification to{" "}
            <b className="text-foreground">{recipientName}</b> for their outstanding balance of{" "}
            <b className="text-primary">{formatMoney(amountUnits, currency)}</b>.
          </p>
          <div className="rounded-xl bg-badge p-3 text-xs text-badge-foreground">
            To prevent spamming, reminders are rate-limited to at most one per hour.
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSend} disabled={busy} className="w-full">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Bell className="mr-2 h-4 w-4" /> Send Reminder Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -------------------------------------------------------------
// EXPORT TRANSACTIONS DIALOG (REAL .XLSX)
// -------------------------------------------------------------

export function ExportDialog({
  title,
  transactions,
  open,
  onOpenChange,
}: {
  title: string;
  transactions: ExportTransaction[];
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  function runExport() {
    exportTransactionsToXlsx(title, transactions, {
      from: from || undefined,
      to: to || undefined,
    });
    toast.success("Excel (.xlsx) workbook downloaded successfully!");
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export to Excel (.xlsx)</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Download a verified Excel workbook with complete financial records, dates, categories,
            currencies, and participant splits.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>From Date</Label>
              <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>To Date</Label>
              <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            All text fields are sanitized to protect against spreadsheet formula injection.
          </p>
        </div>
        <DialogFooter>
          <Button onClick={runExport} className="w-full">
            <Download className="mr-2 h-4 w-4" /> Download .XLSX
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
