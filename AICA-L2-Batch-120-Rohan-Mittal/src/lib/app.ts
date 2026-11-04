import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  Briefcase,
  Car,
  Folder,
  Home,
  Plane,
  ShoppingBag,
  Tag,
  Ticket,
  Users,
  Utensils,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { collection, doc, getDoc, getDocs, query, where, orderBy, limit } from "firebase/firestore";
import { auth, db } from "./firebase";
import {
  formatMoney,
  fromMinorUnits,
  toMinorUnits,
  SUPPORTED_CURRENCIES,
  DEFAULT_CURRENCY,
} from "./currencies";
import {
  netBalances,
  netBalancesByCurrency,
  simplifyDebts,
  calculatePairwiseBalances,
  toCents,
  type Transfer,
} from "./balanceEngine";
import {
  getUserProfile,
  ensureUserProfile,
  type GroupDoc,
  type GroupMemberDoc,
  type ExpenseDoc,
  type SettlementDoc,
  type FriendshipDoc,
  type NotificationDoc,
  type ActivityDoc,
  type UserProfile,
} from "./fairlyshareDb";

export const CATEGORIES: { name: string; icon: LucideIcon }[] = [
  { name: "Food & Drink", icon: Utensils },
  { name: "Transport", icon: Car },
  { name: "Accommodation", icon: Home },
  { name: "Entertainment", icon: Ticket },
  { name: "Groceries", icon: ShoppingBag },
  { name: "Utilities", icon: Zap },
  { name: "Other", icon: Tag },
];

export const GROUP_TYPES: { name: string; icon: LucideIcon }[] = [
  { name: "Trip", icon: Plane },
  { name: "Office", icon: Briefcase },
  { name: "Friends", icon: Users },
  { name: "Home", icon: Home },
  { name: "Other", icon: Folder },
];

export const CURRENCIES = Object.keys(SUPPORTED_CURRENCIES);
export const catIcon = (c: string) => CATEGORIES.find((x) => x.name === c)?.icon ?? Tag;
export const typeIcon = (c: string) => GROUP_TYPES.find((x) => x.name === c)?.icon ?? Folder;

export function money(cents: number, currency: string = DEFAULT_CURRENCY) {
  return formatMoney(cents, currency);
}

export const initials = (n?: string | null) =>
  (n ?? "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("") || "?";

export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const formatDay = (
  iso: string,
  opts: Intl.DateTimeFormatOptions = {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  },
) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y!, (m ?? 1) - 1, d ?? 1).toLocaleDateString("en-US", opts);
};

export const errMsg = (e: unknown) => {
  const m = e instanceof Error ? e.message : (e as { message?: string })?.message;
  if (!m) return "Something went wrong. Please try again.";
  if (m.startsWith("{") && m.includes('"error"')) {
    try {
      const parsed = JSON.parse(m) as { error?: string };
      if (parsed.error) return parsed.error;
    } catch {
      // Fallback to raw message
    }
  }
  if (/network|offline|failed to fetch/i.test(m))
    return "Can't reach the server. Check your connection and try again.";
  return m;
};

export function useUser() {
  const [currentUser, setCurrentUser] = useState<User | null>(auth.currentUser);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setCurrentUser(u);
      setReady(true);
    });
    return () => unsub();
  }, []);

  return useQuery({
    queryKey: ["me", currentUser?.uid, ready],
    enabled: ready,
    queryFn: async () => {
      if (!currentUser) return null;
      let p = await getUserProfile(currentUser.uid);
      if (!p) {
        p = await ensureUserProfile(
          currentUser.uid,
          currentUser.email || "",
          currentUser.displayName || undefined,
          currentUser.photoURL,
        );
      }
      return {
        id: currentUser.uid,
        email: currentUser.email ?? "",
        name: p?.display_name || currentUser.displayName || currentUser.email || "",
        avatar: p?.avatar_url || currentUser.photoURL || null,
        phone_number: p?.phone_number || null,
        email_verified:
          currentUser.emailVerified ||
          currentUser.providerData.some((p) => p.providerId === "google.com"),
      };
    },
  });
}

export function useOnline() {
  const [on, setOn] = useState(true);
  useEffect(() => {
    const u = () => setOn(navigator.onLine);
    u();
    window.addEventListener("online", u);
    window.addEventListener("offline", u);
    return () => {
      window.removeEventListener("online", u);
      window.removeEventListener("offline", u);
    };
  }, []);
  return on;
}

export type Member = GroupMemberDoc;
export type ExpenseRow = {
  id: string;
  description: string;
  amount: number;
  amount_units: number;
  currency: string;
  category: string;
  paid_by_member_id: string;
  paid_by_uid: string;
  split_type: string;
  expense_date: string;
  note: string | null;
  created_by: string | null;
  expense_splits: {
    member_id: string;
    amount: number;
    amount_units: number;
    percentage: number | null;
  }[];
};

export type SettlementRow = {
  id: string;
  from_member_id: string;
  to_member_id: string;
  from_uid: string;
  to_uid: string;
  amount: number;
  amount_units: number;
  currency: string;
  settled_on: string;
  note: string | null;
  created_by: string | null;
};

export type GroupRow = {
  id: string;
  name: string;
  category: string;
  currency: string;
  invite_code: string;
  member_ids: string[];
  archived_at: string | null;
};

export type GroupData = {
  group: GroupRow;
  members: Member[];
  expenses: ExpenseRow[];
  settlements: SettlementRow[];
  net: Record<string, number>;
  netByCurrency: Record<string, Record<string, number>>;
  transfers: Transfer[];
  transfersByCurrency: Record<string, Transfer[]>;
  myMemberId: string | undefined;
};

function computeGroupData(
  group: GroupDoc,
  members: GroupMemberDoc[],
  expenses: ExpenseDoc[],
  settlements: SettlementDoc[],
  uid?: string,
): GroupData {
  const memberIds = members.map((m) => m.id);

  // Grouped expenses converted for math
  const ledgerExpenses = expenses.map((e) => ({
    paidBy:
      e.paid_by_member_id || members.find((m) => m.user_id === e.paid_by_uid)?.id || e.paid_by_uid,
    cents: e.amount_units,
    currency: e.currency,
    shares: e.splits.map((s) => ({
      memberId: s.member_id || members.find((m) => m.user_id === s.user_id)?.id || s.user_id || "",
      cents: s.amount_units,
    })),
  }));

  const ledgerSettlements = settlements.map((s) => ({
    from: s.from_member_id || members.find((m) => m.user_id === s.from_uid)?.id || s.from_uid,
    to: s.to_member_id || members.find((m) => m.user_id === s.to_uid)?.id || s.to_uid,
    cents: s.amount_units,
    currency: s.currency,
  }));

  const netByCurrency = netBalancesByCurrency(memberIds, ledgerExpenses, ledgerSettlements);

  // Default / group currency net
  const groupCurr = group.currency || DEFAULT_CURRENCY;
  const net = netByCurrency[groupCurr] || Object.fromEntries(memberIds.map((id) => [id, 0]));

  const transfers = simplifyDebts(net, groupCurr);
  const transfersByCurrency: Record<string, Transfer[]> = {};
  for (const [c, n] of Object.entries(netByCurrency)) {
    transfersByCurrency[c] = simplifyDebts(n, c);
  }

  const expRows: ExpenseRow[] = expenses.map((e) => ({
    id: e.id,
    description: e.description,
    amount: fromMinorUnits(e.amount_units, e.currency),
    amount_units: e.amount_units,
    currency: e.currency,
    category: e.category,
    paid_by_member_id:
      e.paid_by_member_id || members.find((m) => m.user_id === e.paid_by_uid)?.id || "",
    paid_by_uid: e.paid_by_uid,
    split_type: e.split_type,
    expense_date: e.expense_date,
    note: e.note ?? null,
    created_by: e.created_by,
    expense_splits: e.splits.map((s) => ({
      member_id: s.member_id || members.find((m) => m.user_id === s.user_id)?.id || "",
      amount: fromMinorUnits(s.amount_units, e.currency),
      amount_units: s.amount_units,
      percentage: s.percentage ?? null,
    })),
  }));

  const setRows: SettlementRow[] = settlements.map((s) => ({
    id: s.id,
    from_member_id: s.from_member_id || members.find((m) => m.user_id === s.from_uid)?.id || "",
    to_member_id: s.to_member_id || members.find((m) => m.user_id === s.to_uid)?.id || "",
    from_uid: s.from_uid,
    to_uid: s.to_uid,
    amount: fromMinorUnits(s.amount_units, s.currency),
    amount_units: s.amount_units,
    currency: s.currency,
    settled_on: s.settled_on,
    note: s.note ?? null,
    created_by: s.created_by,
  }));

  return {
    group: {
      id: group.id,
      name: group.name,
      category: group.category,
      currency: group.currency,
      invite_code: group.invite_code,
      member_ids: group.member_ids ?? [],
      archived_at: group.archived_at,
    },
    members,
    expenses: expRows,
    settlements: setRows,
    net,
    netByCurrency,
    transfers,
    transfersByCurrency,
    myMemberId: members.find((m) => m.user_id === uid)?.id,
  };
}

async function loadGroupsForUser(uid: string): Promise<GroupData[]> {
  const qGroups = query(collection(db, "groups"), where("member_ids", "array-contains", uid));
  const snapGroups = await getDocs(qGroups);
  if (snapGroups.empty) return [];

  const groups = snapGroups.docs.map((d) => d.data() as GroupDoc);

  const groupDataList = await Promise.all(
    groups.map(async (g) => {
      // 1. Members
      const membersSnap = await getDocs(collection(db, "groups", g.id, "members"));
      const members = membersSnap.docs.map((d) => d.data() as GroupMemberDoc);

      // 2. Expenses
      let expenses: ExpenseDoc[] = [];
      try {
        const expQ = query(collection(db, "expenses"), where("group_id", "==", g.id));
        const expSnap = await getDocs(expQ);
        expenses = expSnap.docs
          .map((d) => d.data() as ExpenseDoc)
          .sort((a, b) => b.expense_date.localeCompare(a.expense_date));
      } catch {
        expenses = [];
      }

      // 3. Settlements
      let settlements: SettlementDoc[] = [];
      try {
        const setQ = query(collection(db, "settlements"), where("group_id", "==", g.id));
        const setSnap = await getDocs(setQ);
        settlements = setSnap.docs
          .map((d) => d.data() as SettlementDoc)
          .sort((a, b) => b.settled_on.localeCompare(a.settled_on));
      } catch {
        settlements = [];
      }

      return computeGroupData(g, members, expenses, settlements, uid);
    }),
  );

  return groupDataList;
}

export function useAllGroups() {
  const { data: me } = useUser();
  return useQuery({
    queryKey: ["groups", me?.id],
    enabled: !!me?.id,
    queryFn: async () => loadGroupsForUser(me!.id),
  });
}

export function useGroup(groupId: string) {
  const { data: me } = useUser();
  return useQuery({
    queryKey: ["group", groupId, me?.id],
    enabled: !!me?.id && !!groupId,
    queryFn: async () => {
      const gDoc = await getDoc(doc(db, "groups", groupId));
      if (!gDoc.exists()) return null;
      const g = gDoc.data() as GroupDoc;

      const membersSnap = await getDocs(collection(db, "groups", g.id, "members"));
      const members = membersSnap.docs.map((d) => d.data() as GroupMemberDoc);

      let expenses: ExpenseDoc[] = [];
      try {
        const expQ = query(collection(db, "expenses"), where("group_id", "==", g.id));
        const expSnap = await getDocs(expQ);
        expenses = expSnap.docs
          .map((d) => d.data() as ExpenseDoc)
          .sort((a, b) => b.expense_date.localeCompare(a.expense_date));
      } catch {
        expenses = [];
      }

      let settlements: SettlementDoc[] = [];
      try {
        const setQ = query(collection(db, "settlements"), where("group_id", "==", g.id));
        const setSnap = await getDocs(setQ);
        settlements = setSnap.docs
          .map((d) => d.data() as SettlementDoc)
          .sort((a, b) => b.settled_on.localeCompare(a.settled_on));
      } catch {
        settlements = [];
      }

      return computeGroupData(g, members, expenses, settlements, me?.id);
    },
  });
}

// -------------------------------------------------------------
// FRIENDS HOOKS
// -------------------------------------------------------------

export interface FriendSummary {
  friendship: FriendshipDoc;
  friendUser:
    UserProfile | { id: string; display_name: string; email: string; avatar_url: string | null };
  pairwiseBalances: Record<string, number>; // currency -> net integer minor units. > 0: they owe me, < 0: I owe them
  directExpenses: ExpenseDoc[];
  directSettlements: SettlementDoc[];
  totalDirectExpensesCount: number;
}

export function useFriends() {
  const { data: me } = useUser();
  return useQuery({
    queryKey: ["friends", me?.id],
    enabled: !!me?.id,
    queryFn: async () => {
      const uid = me!.id;

      // 1. Find all friendships (by UID and by email)
      const fQ = query(collection(db, "friendships"), where("users", "array-contains", uid));
      const fSnap = await getDocs(fQ);
      const byId = new Map<string, FriendshipDoc>();
      for (const d of fSnap.docs) {
        const docData = d.data() as FriendshipDoc;
        byId.set(docData.id, docData);
      }

      if (me?.email) {
        try {
          const emailQ = query(
            collection(db, "friendships"),
            where("receiver_email", "==", me.email.trim().toLowerCase()),
          );
          const emailSnap = await getDocs(emailQ);
          for (const d of emailSnap.docs) {
            const docData = d.data() as FriendshipDoc;
            byId.set(docData.id, docData);
          }
        } catch {
          // Non-fatal
        }
      }

      const friendships = Array.from(byId.values());

      // 2. Fetch all direct and group expenses for user
      const expQ = query(
        collection(db, "expenses"),
        where("participant_uids", "array-contains", uid),
      );
      const expSnap = await getDocs(expQ);
      const allUserExpenses = expSnap.docs.map((d) => d.data() as ExpenseDoc);

      const setQ = query(
        collection(db, "settlements"),
        where("participant_uids", "array-contains", uid),
      );
      const setSnap = await getDocs(setQ);
      const allUserSettlements = setSnap.docs.map((d) => d.data() as SettlementDoc);

      const rawSummaries = await Promise.all(
        friendships.map(async (f): Promise<FriendSummary | null> => {
          const otherUid = f.users.find((u) => u !== uid) || f.receiver_id;
          let otherProfile: UserProfile | null = null;
          if (otherUid) {
            otherProfile = await getUserProfile(otherUid);
          }

          // Exclude deleted users from appearing in the Friends list
          if (
            otherProfile?.is_deleted === true ||
            otherProfile?.display_name === "Deleted user" ||
            (f.status === "accepted" && otherUid && !otherProfile)
          ) {
            return null;
          }

          const friendUser = otherProfile || {
            id: otherUid || f.id,
            display_name: f.receiver_email ? f.receiver_email.split("@")[0]! : "Friend",
            email: f.receiver_email || "",
            avatar_url: null,
          };

          // Pairwise calculations including BOTH direct expenses AND shared group expenses
          const relevantExpenses = otherUid
            ? allUserExpenses.filter((e) => e.participant_uids.includes(otherUid))
            : [];
          const relevantSettlements = otherUid
            ? allUserSettlements.filter((s) => s.participant_uids.includes(otherUid))
            : [];

          const ledgerExpenses = relevantExpenses.map((e) => ({
            paidBy: e.paid_by_uid,
            cents: e.amount_units,
            currency: e.currency,
            shares: e.splits.map((s) => ({
              memberId: s.user_id || "",
              cents: s.amount_units,
            })),
          }));

          const ledgerSettlements = relevantSettlements.map((s) => ({
            from: s.from_uid,
            to: s.to_uid,
            cents: s.amount_units,
            currency: s.currency,
          }));

          const pairwiseBalances = otherUid
            ? calculatePairwiseBalances(uid, otherUid, ledgerExpenses, ledgerSettlements)
            : {};

          const directExpenses = relevantExpenses.filter((e) => !e.group_id);
          const directSettlements = relevantSettlements.filter((s) => !s.group_id);

          return {
            friendship: f,
            friendUser,
            pairwiseBalances,
            directExpenses,
            directSettlements,
            totalDirectExpensesCount: directExpenses.length,
          };
        }),
      );

      return rawSummaries.filter((s): s is FriendSummary => s !== null);
    },
  });
}

// -------------------------------------------------------------
// NOTIFICATIONS & ACTIVITY
// -------------------------------------------------------------

export function useNotifications() {
  const { data: me } = useUser();
  return useQuery({
    queryKey: ["notifications", me?.id],
    enabled: !!me?.id,
    queryFn: async () => {
      const q1 = query(collection(db, "notifications"), where("recipient_uid", "==", me!.id));
      const snap = await getDocs(q1);
      return snap.docs
        .map((d) => d.data() as NotificationDoc)
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .slice(0, 50);
    },
  });
}

export function useRecentActivity() {
  const { data: me } = useUser();
  return useQuery({
    queryKey: ["activity", me?.id],
    enabled: !!me?.id,
    queryFn: async () => {
      const q1 = query(
        collection(db, "activity"),
        where("participant_uids", "array-contains", me!.id),
      );
      const snap = await getDocs(q1);
      return snap.docs
        .map((d) => d.data() as ActivityDoc)
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .slice(0, 30);
    },
  });
}
