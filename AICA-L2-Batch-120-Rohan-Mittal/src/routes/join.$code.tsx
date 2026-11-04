import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, RefreshCw, UserCheck, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";
import {
  isSignInWithEmailLink,
  onAuthStateChanged,
  signInWithEmailLink,
  type User,
} from "firebase/auth";
import { collection, doc, getDoc, getDocs, limit, query, where } from "firebase/firestore";
import { auth, db } from "@/lib/firebase";
import {
  acceptFriendInviteByCode,
  ensureUserProfile,
  getUserProfile,
  joinGroup,
  type FriendshipDoc,
  type GroupDoc,
  type GroupMemberDoc,
} from "@/lib/fairlyshareDb";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { errMsg, typeIcon } from "@/lib/app";
import { AuthCard } from "./auth";

export const Route = createFileRoute("/join/$code")({
  ssr: false,
  validateSearch: (s: Record<string, unknown>) => ({
    claim: typeof s["claim"] === "string" ? s["claim"] : undefined,
    invitedBy: typeof s["invitedBy"] === "string" ? s["invitedBy"] : undefined,
    inviteEmail: typeof s["inviteEmail"] === "string" ? s["inviteEmail"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Accept Invite — Fair Share" },
      { name: "description", content: "You've been invited to split expenses on Fair Share." },
      { property: "og:title", content: "Accept Invite — Fair Share" },
      {
        property: "og:description",
        content: "You've been invited to split expenses on Fair Share.",
      },
    ],
  }),
  component: JoinPage,
});

type GroupPreview = {
  kind: "group";
  group_id: string;
  name: string;
  category: string;
  currency: string;
  member_count: number;
  archived: boolean;
  already_member: boolean;
  claim_name: string | null;
  claim_valid: boolean;
};

type FriendPreview = {
  kind: "friend";
  sender_uid: string;
  sender_name: string;
  sender_email: string | null;
  already_friends: boolean;
  is_self: boolean;
};

type Preview = GroupPreview | FriendPreview;

function JoinPage() {
  const { code } = Route.useParams();
  const { claim, invitedBy, inviteEmail } = Route.useSearch();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [authedUser, setAuthedUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const searchSuffix = new URLSearchParams();
  if (claim) searchSuffix.set("claim", claim);
  if (invitedBy) searchSuffix.set("invitedBy", invitedBy);
  if (inviteEmail) searchSuffix.set("inviteEmail", inviteEmail);
  const qs = searchSuffix.toString();
  const here = `/join/${code}${qs ? `?${qs}` : ""}`;

  useEffect(() => {
    let active = true;

    async function handleAuthInit() {
      // If user arrived via auto-generated Fair Share email sign-in link, sign them in automatically
      if (
        typeof window !== "undefined" &&
        !auth.currentUser &&
        isSignInWithEmailLink(auth, window.location.href) &&
        inviteEmail
      ) {
        try {
          const cred = await signInWithEmailLink(auth, inviteEmail.trim(), window.location.href);
          await ensureUserProfile(
            cred.user.uid,
            cred.user.email || inviteEmail.trim(),
            cred.user.displayName || inviteEmail.split("@")[0] || "Member",
          );
          if (active) {
            setAuthedUser(cred.user);
            setReady(true);
          }
          return;
        } catch (err) {
          console.warn("Email link auto sign-in note:", err);
        }
      }

      const unsub = onAuthStateChanged(auth, (user) => {
        if (!active) return;
        setAuthedUser(user);
        setReady(true);
        if (!user) {
          navigate({ to: "/auth", search: { redirect: here }, replace: true });
        }
      });
      return unsub;
    }

    const cleanupPromise = handleAuthInit();
    return () => {
      active = false;
      cleanupPromise.then((unsub) => unsub?.());
    };
  }, [here, inviteEmail, navigate]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["preview", code, claim, authedUser?.uid],
    enabled: ready && !!authedUser,
    queryFn: async (): Promise<Preview | null> => {
      const trimmed = code.trim();

      // 1. Check if this is a Friend Invite Link (friend_<uid> or invitations doc of type 'friend')
      let friendSenderUid: string | null = null;
      let fallbackSenderName = invitedBy || "Your friend";

      if (trimmed.startsWith("friend_")) {
        friendSenderUid = trimmed.slice("friend_".length);
      } else {
        try {
          const invSnap = await getDoc(doc(db, "invitations", trimmed));
          if (invSnap.exists() && invSnap.data().type === "friend") {
            friendSenderUid = invSnap.data().sender_uid;
            if (invSnap.data().sender_name) {
              fallbackSenderName = invSnap.data().sender_name;
            }
          }
        } catch {
          // Proceed to group check
        }
      }

      if (friendSenderUid) {
        const senderProfile = await getUserProfile(friendSenderUid);
        const senderName = senderProfile?.display_name || fallbackSenderName;
        const senderEmail = senderProfile?.email || null;
        const isSelf = friendSenderUid === authedUser!.uid;

        let alreadyFriends = false;
        if (!isSelf) {
          const fid = [friendSenderUid, authedUser!.uid].sort().join("_");
          const fSnap = await getDoc(doc(db, "friendships", fid));
          if (fSnap.exists()) {
            const fData = fSnap.data() as FriendshipDoc;
            alreadyFriends = fData.status === "accepted";
          }
        }

        return {
          kind: "friend",
          sender_uid: friendSenderUid,
          sender_name: senderName,
          sender_email: senderEmail,
          already_friends: alreadyFriends,
          is_self: isSelf,
        };
      }

      // 2. Otherwise check if this is a Group Invite Code
      const gQ = query(collection(db, "groups"), where("invite_code", "==", trimmed), limit(1));
      const snap = await getDocs(gQ);
      if (snap.empty) return null;
      const grp = snap.docs[0]!.data() as GroupDoc;

      const memSnap = await getDocs(collection(db, "groups", grp.id, "members"));
      const members = memSnap.docs.map((d) => d.data() as GroupMemberDoc);

      const already = members.some((m) => m.user_id === authedUser!.uid);
      let claim_name: string | null = null;
      let claim_valid = false;

      if (claim && claim.trim()) {
        const found = members.find(
          (m) =>
            m.claim_token === claim.trim() &&
            !m.user_id &&
            m.claim_token_expires_at &&
            new Date(m.claim_token_expires_at).getTime() > Date.now(),
        );
        if (found) {
          claim_name = found.name;
          claim_valid = true;
        }
      }

      return {
        kind: "group",
        group_id: grp.id,
        name: grp.name,
        category: grp.category,
        currency: grp.currency,
        member_count: members.length,
        archived: !!grp.archived_at,
        already_member: already,
        claim_name,
        claim_valid,
      };
    },
  });

  async function acceptFriendInvite() {
    setBusy(true);
    try {
      const res = await acceptFriendInviteByCode(code);
      await qc.invalidateQueries({ queryKey: ["friends"] });
      toast.success(`You and ${res.senderName} are now connected as friends!`);
      navigate({ to: "/" });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  async function join(useClaim: boolean) {
    setBusy(true);
    try {
      const gid = await joinGroup(code, useClaim ? claim : undefined);
      await qc.invalidateQueries({ queryKey: ["groups"] });
      toast.success("You're in!");
      navigate({ to: "/group/$groupId", params: { groupId: gid }, search: { add: undefined } });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  if (!ready || isLoading) {
    return (
      <AuthCard title="Loading invite…" subtitle="Just a moment">
        <Skeleton className="h-24 rounded-2xl" />
      </AuthCard>
    );
  }

  if (error) {
    return (
      <AuthCard title="Couldn't load invite" subtitle={errMsg(error)}>
        <Button className="w-full" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Try again
        </Button>
      </AuthCard>
    );
  }

  if (!data) {
    return (
      <AuthCard
        title="Invite not found"
        subtitle="This link is invalid or was reset. Ask your friend or group admin for a fresh link."
      >
        <Button className="w-full" onClick={() => navigate({ to: "/" })}>
          Go home
        </Button>
      </AuthCard>
    );
  }

  // Friend Invite UI
  if (data.kind === "friend") {
    if (data.is_self) {
      return (
        <AuthCard
          title="Your Friend Invite Link"
          subtitle="Share this link on WhatsApp, email, or message so friends can connect with you."
        >
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This is your own personal Fair Share invite link. When a friend opens it, you will
              both appear in each other&apos;s Friends list and can add each other to any group.
            </p>
            <Button
              className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
              onClick={() => navigate({ to: "/" })}
            >
              Back to Dashboard
            </Button>
          </div>
        </AuthCard>
      );
    }

    if (data.already_friends) {
      return (
        <AuthCard
          title={`Connected with ${data.sender_name}`}
          subtitle="You are already in each other's Friends list on Fair Share."
        >
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-2xl border border-[#BAE6FD] bg-[#F0F8FF] p-4">
              <CheckCircle2 className="h-6 w-6 text-[#0284C7] shrink-0" />
              <div className="text-xs text-[#0F2744]">
                <p className="font-bold text-sm">{data.sender_name}</p>
                <p className="text-muted-foreground">
                  You can split direct expenses or add {data.sender_name} to any group.
                </p>
              </div>
            </div>
            <Button
              className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
              onClick={() => navigate({ to: "/" })}
            >
              Go to Dashboard
            </Button>
          </div>
        </AuthCard>
      );
    }

    return (
      <AuthCard
        title="Friend Invitation"
        subtitle={`${data.sender_name} has invited you to join Fair Share`}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-2xl border border-[#BAE6FD] bg-[#F0F8FF] p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#0F2744] text-[#38BDF8] shrink-0">
              <UserCheck className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-sm text-[#0F2744] truncate">{data.sender_name}</p>
              {data.sender_email && (
                <p className="text-xs text-muted-foreground truncate">{data.sender_email}</p>
              )}
              <p className="text-xs text-[#0284C7] mt-0.5 font-medium">
                Wants to split expenses &amp; groups with you
              </p>
            </div>
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed">
            Accepting this invite connects you and{" "}
            <b className="text-foreground">{data.sender_name}</b> as friends so you both see each
            other in your Friends list and can add each other to any group.
          </p>

          <Button
            className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
            onClick={acceptFriendInvite}
            disabled={busy}
          >
            {busy ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <UserPlus className="mr-2 h-4 w-4 text-[#38BDF8]" />
            )}
            Accept &amp; Add {data.sender_name} as Friend
          </Button>
        </div>
      </AuthCard>
    );
  }

  // Group Invite UI
  const Icon = typeIcon(data.category);
  const header = (
    <div className="mb-5 flex items-center gap-3">
      <div className="rounded-xl bg-badge p-2.5 text-badge-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-sm text-muted-foreground">
        {data.category} · {data.member_count} members · {data.currency}
      </div>
    </div>
  );

  if (data.already_member) {
    return (
      <AuthCard title={data.name} subtitle="You're already a member of this group">
        {header}
        <Button
          className="w-full"
          onClick={() =>
            navigate({
              to: "/group/$groupId",
              params: { groupId: data.group_id },
              search: { add: undefined },
            })
          }
        >
          Open group
        </Button>
      </AuthCard>
    );
  }

  if (data.archived) {
    return (
      <AuthCard
        title={data.name}
        subtitle="This group is archived and isn't accepting new members."
      >
        {header}
        <Button className="w-full" onClick={() => navigate({ to: "/" })}>
          Go home
        </Button>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title={data.name}
      subtitle={
        invitedBy
          ? `${invitedBy} invited you to join this group on Fair Share`
          : "You've been invited to join this group"
      }
    >
      {header}
      {claim && !data.claim_valid && (
        <p className="mb-4 rounded-xl bg-owe-soft p-3 text-xs text-owe">
          This personal link is invalid, expired, or already used. You can still join as a new
          member, or ask the admin for a fresh link.
        </p>
      )}
      {data.claim_valid && data.claim_name ? (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            The admin set this link up for <b className="text-foreground">{data.claim_name}</b>.
            Joining links you to their existing expenses.
          </p>
          <Button className="w-full" onClick={() => join(true)} disabled={busy}>
            {busy ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Users className="mr-2 h-4 w-4" />
            )}
            Join as {data.claim_name}
          </Button>
          <Button variant="outline" className="w-full" onClick={() => join(false)} disabled={busy}>
            I&apos;m someone else, join as new
          </Button>
        </div>
      ) : (
        <Button className="w-full" onClick={() => join(false)} disabled={busy}>
          {busy ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="mr-2 h-4 w-4" />
          )}
          Join group
        </Button>
      )}
    </AuthCard>
  );
}
