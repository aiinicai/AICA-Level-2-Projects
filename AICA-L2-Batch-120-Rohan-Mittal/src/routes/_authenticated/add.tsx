import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, Clock, Plus, Receipt, User, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, MemberAvatar } from "@/components/AppShell";
import { CreateGroupDialog, AddFriendDialog, ExpenseDialog } from "@/components/Dialogs";
import { typeIcon, useAllGroups, useFriends, useUser } from "@/lib/app";

export const Route = createFileRoute("/_authenticated/add")({
  head: () => ({
    meta: [
      { title: "Add expense — Fair Share" },
      { name: "description", content: "Pick a group or friend and add a shared expense." },
      { property: "og:title", content: "Add expense — Fair Share" },
      { property: "og:description", content: "Pick a group or friend and add a shared expense." },
    ],
  }),
  component: AddExpensePage,
});

function AddExpensePage() {
  const { data: user } = useUser();
  const myUid = user?.id || "";

  const { data: groups, isLoading: loadingGroups } = useAllGroups();
  const { data: friends, isLoading: loadingFriends } = useFriends();
  const [groupDialogOpen, setGroupDialogOpen] = useState(false);
  const [friendDialogOpen, setFriendDialogOpen] = useState(false);
  const [directFriend, setDirectFriend] = useState<{
    id: string;
    name: string;
    friendshipId: string;
  } | null>(null);
  const [directExpenseOpen, setDirectExpenseOpen] = useState(false);

  // User-scoped last saved preferences (group and currency)
  const lastSavedPrefs = useMemo<{ groupId: string | null; currency: string } | null>(() => {
    if (!myUid) return null;
    try {
      const raw = localStorage.getItem(`fairlyshare_last_prefs_${myUid}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }, [myUid]);

  // Sort groups placing user-scoped last used group at the top if still accessible
  const sortedGroups = useMemo(() => {
    if (!groups) return [];
    if (!lastSavedPrefs?.groupId) return groups;
    const matchIdx = groups.findIndex((g) => g.group.id === lastSavedPrefs.groupId);
    if (matchIdx <= 0) return groups;
    const recent = groups[matchIdx];
    if (!recent) return groups;
    const rest = groups.filter((_, i) => i !== matchIdx);
    return [recent, ...rest];
  }, [groups, lastSavedPrefs?.groupId]);

  const [quickGroup, setQuickGroup] = useState<(typeof sortedGroups)[number] | null>(null);
  const initializedForUser = useRef<string | null>(null);
  useEffect(() => {
    if (!myUid || !groups || initializedForUser.current === myUid) return;
    initializedForUser.current = myUid;
    const remembered = groups.find((group) => group.group.id === lastSavedPrefs?.groupId);
    if (remembered) setQuickGroup(remembered);
  }, [myUid, groups, lastSavedPrefs?.groupId]);

  // Rank accepted friends by actual activity timestamp (most recent first)
  const recentAcceptedFriends = useMemo(() => {
    const list = friends?.filter((f) => f.friendship.status === "accepted") ?? [];
    return list
      .map((f) => {
        let latestMs = 0;
        for (const e of f.directExpenses) {
          const d = new Date(e.expense_date || e.created_at).getTime();
          if (!isNaN(d) && d > latestMs) latestMs = d;
        }
        for (const s of f.directSettlements) {
          const d = new Date(s.settled_on || s.created_at).getTime();
          if (!isNaN(d) && d > latestMs) latestMs = d;
        }
        const fDate = new Date(f.friendship.updated_at || f.friendship.created_at).getTime();
        if (!isNaN(fDate) && latestMs === 0) latestMs = fDate;
        return { friend: f, latestMs };
      })
      .sort((a, b) => b.latestMs - a.latestMs)
      .map((item) => item.friend);
  }, [friends]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Add expense</h1>
        <p className="text-sm text-muted-foreground">Select a group or a friend to split with.</p>
      </div>

      {/* Groups Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" /> With a Group
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setGroupDialogOpen(true)}
            className="text-xs"
          >
            <Plus className="mr-1 h-3.5 w-3.5" /> New Group
          </Button>
        </div>

        {loadingGroups ? (
          <div className="space-y-2">
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-16 rounded-2xl" />
            ))}
          </div>
        ) : !sortedGroups.length ? (
          <div className="rounded-2xl border border-dashed p-4 text-center text-xs text-muted-foreground">
            No groups yet.{" "}
            <button
              type="button"
              onClick={() => setGroupDialogOpen(true)}
              className="text-primary font-semibold underline"
            >
              Create a group
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {sortedGroups.map((g) => {
              const I = typeIcon(g.group.category);
              const isRecent = lastSavedPrefs?.groupId === g.group.id;
              return (
                <Link
                  key={g.group.id}
                  to="/group/$groupId"
                  params={{ groupId: g.group.id }}
                  search={{ add: true }}
                  className={`flex items-center gap-3 rounded-2xl border bg-card p-4 shadow-soft hover:bg-muted/30 transition ${
                    isRecent ? "ring-2 ring-primary/20 border-primary/40" : ""
                  }`}
                >
                  <div className="rounded-xl bg-badge p-2 text-badge-foreground">
                    <I className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground truncate">{g.group.name}</span>
                      {isRecent && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                          <Clock className="h-3 w-3" /> Recent
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {g.members.length} members · {g.group.currency}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* Direct Friends Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
            <User className="h-4 w-4 text-primary" /> Directly with a Friend
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setFriendDialogOpen(true)}
            className="text-xs"
          >
            <Plus className="mr-1 h-3.5 w-3.5" /> Add Friend
          </Button>
        </div>

        {loadingFriends ? (
          <div className="space-y-2">
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-16 rounded-2xl" />
            ))}
          </div>
        ) : !recentAcceptedFriends.length ? (
          <div className="rounded-2xl border border-dashed p-4 text-center text-xs text-muted-foreground">
            No friends added yet.{" "}
            <button
              type="button"
              onClick={() => setFriendDialogOpen(true)}
              className="text-primary font-semibold underline"
            >
              Add a friend
            </button>{" "}
            to split one-on-one.
          </div>
        ) : (
          <div className="space-y-2">
            {recentAcceptedFriends.map((f) => (
              <button
                type="button"
                key={f.friendship.id}
                onClick={() => {
                  setDirectFriend({
                    id: f.friendUser.id,
                    name: f.friendUser.display_name,
                    friendshipId: f.friendship.id,
                  });
                  setDirectExpenseOpen(true);
                }}
                className="w-full flex items-center gap-3 rounded-2xl border bg-card p-4 shadow-soft hover:bg-muted/30 transition text-left"
              >
                <MemberAvatar name={f.friendUser.display_name} src={f.friendUser.avatar_url} />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-foreground truncate">
                    {f.friendUser.display_name}
                  </div>
                  <div className="text-xs text-muted-foreground">{f.friendUser.email}</div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}
      </div>

      {quickGroup && (
        <ExpenseDialog
          data={quickGroup}
          open
          onOpenChange={(open) => {
            if (!open) setQuickGroup(null);
          }}
        />
      )}
      <CreateGroupDialog open={groupDialogOpen} onOpenChange={setGroupDialogOpen} />
      <AddFriendDialog open={friendDialogOpen} onOpenChange={setFriendDialogOpen} />
      {directFriend && (
        <ExpenseDialog
          directFriend={directFriend}
          open={directExpenseOpen}
          onOpenChange={(o) => {
            setDirectExpenseOpen(o);
            if (!o) setDirectFriend(null);
          }}
        />
      )}
    </div>
  );
}
