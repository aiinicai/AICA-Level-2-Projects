import {
  collection,
  doc,
  getDoc,
  getDocs,
  setDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  serverTimestamp,
  Timestamp,
  writeBatch,
} from "firebase/firestore";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  sendEmailVerification,
  sendPasswordResetEmail,
  GoogleAuthProvider,
  EmailAuthProvider,
  linkWithCredential,
  updateProfile,
} from "firebase/auth";
import { auth, db, handleFirestoreError, OperationType } from "./firebase";
import { getCurrencyInfo, toMinorUnits, fromMinorUnits, formatMoney } from "./currencies";
import {
  netBalancesByCurrency,
  calculatePairwiseBalances,
  simplifyDebts,
  type Share,
  type Transfer,
} from "./balanceEngine";

// Types
export interface UserProfile {
  id: string;
  email: string;
  email_verified: boolean;
  display_name: string;
  phone_number?: string | null;
  avatar_url?: string | null;
  is_deleted?: boolean;
  push_tokens?: string[];
  created_at: string;
  updated_at: string;
}

export interface GroupDoc {
  id: string;
  name: string;
  category: "Trip" | "Office" | "Friends" | "Home" | "Other";
  currency: string;
  invite_code: string;
  created_by: string;
  member_ids: string[];
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GroupMemberDoc {
  id: string;
  group_id: string;
  user_id: string | null;
  name: string;
  email: string | null;
  avatar_url: string | null;
  role: "admin" | "member";
  claim_token: string | null;
  claim_token_expires_at: string | null;
  joined_at: string;
}

export interface ExpenseSplit {
  member_id?: string;
  user_id?: string;
  amount_units: number;
  percentage?: number | null;
}

export interface ExpenseDoc {
  id: string;
  group_id?: string | null;
  friendship_id?: string | null;
  participant_uids: string[];
  description: string;
  amount_units: number;
  currency: string;
  category: string;
  paid_by_member_id?: string | null;
  paid_by_uid: string;
  split_type: "EQUAL" | "EXACT" | "PERCENTAGE";
  expense_date: string;
  note?: string | null;
  created_by: string;
  splits: ExpenseSplit[];
  created_at: string;
  updated_at: string;
}

export interface SettlementDoc {
  id: string;
  group_id?: string | null;
  friendship_id?: string | null;
  participant_uids: string[];
  from_member_id?: string | null;
  to_member_id?: string | null;
  from_uid: string;
  to_uid: string;
  amount_units: number;
  currency: string;
  settled_on: string;
  note?: string | null;
  created_by: string;
  created_at: string;
}

export interface FriendshipDoc {
  id: string;
  users: string[]; // [userA, userB] sorted
  sender_id: string;
  receiver_id?: string | null;
  receiver_email?: string | null;
  status: "pending" | "accepted" | "declined";
  created_at: string;
  updated_at: string;
}

export interface NotificationDoc {
  id: string;
  recipient_uid: string;
  sender_uid: string;
  sender_name: string;
  type: "reminder" | "friend_request" | "friend_accepted" | "expense_added" | "settlement_recorded";
  title: string;
  message: string;
  target_type: "group" | "friend" | "expense" | "settlement";
  target_id: string;
  currency?: string;
  amount_units?: number;
  is_read: boolean;
  created_at: string;
}

export interface ActivityDoc {
  id: string;
  group_id?: string | null;
  friendship_id?: string | null;
  participant_uids: string[];
  actor_uid: string;
  actor_name: string;
  action: string;
  description: string;
  currency?: string | null;
  amount_units?: number | null;
  created_at: string;
}

// Helper: generate unguessable random alphanumeric ID
export function generateToken(length = 24): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const arr = new Uint8Array(length);
  crypto.getRandomValues(arr);
  return Array.from(arr, (n) => chars[n % chars.length]).join("");
}

// -------------------------------------------------------------
// AUTH & PROFILE
// -------------------------------------------------------------

export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  try {
    const snap = await getDoc(doc(db, "users", uid));
    if (!snap.exists()) return null;
    return snap.data() as UserProfile;
  } catch (err) {
    handleFirestoreError(err, OperationType.GET, `users/${uid}`);
  }
}

export async function ensureUserProfile(
  uid: string,
  email: string,
  name?: string,
  photo?: string | null,
): Promise<UserProfile> {
  const ref = doc(db, "users", uid);
  const normalizedEmail = (email || "").trim().toLowerCase();
  try {
    const snap = await getDoc(ref);
    const now = new Date().toISOString();
    let resultProfile: UserProfile;

    const cleanName =
      name && !name.toLowerCase().includes("invited you to join") ? name.trim() : undefined;

    if (snap.exists()) {
      const existing = snap.data() as UserProfile;
      const updates: Partial<UserProfile> = {
        updated_at: now,
        email_verified: auth.currentUser?.emailVerified ?? existing.email_verified,
      };
      if (
        (!existing.display_name ||
          existing.display_name.toLowerCase().includes("invited you to join")) &&
        cleanName
      ) {
        updates.display_name = cleanName;
      }
      if (!existing.avatar_url && photo) updates.avatar_url = photo;
      await updateDoc(ref, updates as Record<string, unknown>);
      resultProfile = { ...existing, ...updates };
    } else {
      const profile: UserProfile = {
        id: uid,
        email: normalizedEmail,
        email_verified: auth.currentUser?.emailVerified ?? false,
        display_name: cleanName || normalizedEmail.split("@")[0] || "User",
        phone_number: null,
        avatar_url: photo || null,
        is_deleted: false,
        push_tokens: [],
        created_at: now,
        updated_at: now,
      };
      await setDoc(ref, profile);
      resultProfile = profile;
    }

    // Link any pending email-based friend requests and group invites sent to this user's email
    if (normalizedEmail) {
      try {
        const pendingQ = query(
          collection(db, "friendships"),
          where("receiver_email", "==", normalizedEmail),
        );
        const pendingSnap = await getDocs(pendingQ);
        for (const d of pendingSnap.docs) {
          const fData = d.data() as FriendshipDoc;
          if (!fData.users.includes(uid)) {
            const updatedUsers = Array.from(new Set([...fData.users, uid])).sort();
            await updateDoc(doc(db, "friendships", fData.id), {
              receiver_id: uid,
              users: updatedUsers,
              updated_at: now,
            });
          }
        }
      } catch {
        // Non-fatal if no pending email friendships
      }

      try {
        const invQ = query(
          collection(db, "invitations"),
          where("receiver_email", "==", normalizedEmail),
        );
        const invSnap = await getDocs(invQ);
        for (const invDoc of invSnap.docs) {
          const inv = invDoc.data() as {
            id: string;
            type?: string;
            group_id?: string;
            member_id?: string;
          };
          if (inv.type === "group_email" && inv.group_id && inv.member_id) {
            const gRef = doc(db, "groups", inv.group_id);
            const gSnap = await getDoc(gRef);
            if (gSnap.exists()) {
              const gData = gSnap.data() as GroupDoc;
              const batch = writeBatch(db);
              batch.update(doc(db, "groups", inv.group_id, "members", inv.member_id), {
                user_id: uid,
                name: resultProfile.display_name,
                email: normalizedEmail,
                avatar_url: resultProfile.avatar_url ?? null,
                claim_token: null,
                claim_token_expires_at: null,
              });
              batch.update(gRef, {
                member_ids: Array.from(new Set([...(gData.member_ids ?? []), uid])),
                updated_at: now,
              });
              await batch.commit();
            }
          }
        }
      } catch {
        // Non-fatal if no pending group email invitations
      }
    }

    return resultProfile;
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, `users/${uid}`);
  }
}

export async function updateUserProfile(
  uid: string,
  fields: { display_name?: string; phone_number?: string; avatar_url?: string },
): Promise<void> {
  const ref = doc(db, "users", uid);
  try {
    const payload: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };
    if (fields.display_name !== undefined) payload.display_name = fields.display_name.trim();
    if (fields.phone_number !== undefined)
      payload.phone_number = fields.phone_number.trim() || null;
    if (fields.avatar_url !== undefined) payload.avatar_url = fields.avatar_url.trim() || null;

    if (auth.currentUser && fields.display_name) {
      await updateProfile(auth.currentUser, { displayName: fields.display_name.trim() });
    }
    await updateDoc(ref, payload);
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, `users/${uid}`);
  }
}

export async function linkEmailPasswordAccount(password: string): Promise<void> {
  const user = auth.currentUser;
  if (!user || !user.email) throw new Error("No authenticated user with an email address.");
  const cred = EmailAuthProvider.credential(user.email, password);
  await linkWithCredential(user, cred);
}

// -------------------------------------------------------------
// AUTO-GENERATED EMAIL DISPATCHER & FRIEND INVITES
// -------------------------------------------------------------

export function getInviteTempPassword(email: string): string {
  const norm = email.trim().toLowerCase();
  let hash = 2166136261;
  for (let i = 0; i < norm.length; i++) {
    hash ^= norm.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  const hex = (hash >>> 0).toString(16).padStart(8, "0");
  return `FS_Inv_${hex}_9a!Z`;
}

export async function sendAutoGeneratedInviteEmail(params: {
  recipientEmail: string;
  senderName: string;
  inviteUrl: string;
  groupName?: string;
}): Promise<boolean> {
  const normalizedEmail = params.recipientEmail.trim().toLowerCase();
  if (!normalizedEmail || !/^\S+@\S+\.\S+$/.test(normalizedEmail)) return false;

  try {
    const apiKey = auth.app.options.apiKey;
    if (!apiKey) return false;

    const urlObj = new URL(
      params.inviteUrl,
      typeof window !== "undefined" ? window.location.origin : "https://fairshare-rm.ai.studio",
    );
    urlObj.searchParams.set("invitedBy", params.senderName);
    urlObj.searchParams.set("inviteEmail", normalizedEmail);
    if (params.groupName) {
      urlObj.searchParams.set("groupName", params.groupName);
    }
    const continueUrl = urlObj.toString();
    const inviteDisplayName = params.groupName
      ? `${params.senderName} invited you to join "${params.groupName}" on Fair Share`
      : `${params.senderName} invited you to join Fair Share`;
    const tempPassword = getInviteTempPassword(normalizedEmail);

    const sendVerifyOob = async (idToken: string): Promise<boolean> => {
      const withUrlRes = await fetch(
        `https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=${encodeURIComponent(apiKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requestType: "VERIFY_EMAIL",
            idToken,
            continueUrl,
          }),
        },
      );
      if (withUrlRes.ok) return true;

      // Fallback without continueUrl in case the preview/Cloud Run domain is not whitelisted in Firebase Auth OOB settings
      const fallbackRes = await fetch(
        `https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=${encodeURIComponent(apiKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requestType: "VERIFY_EMAIL",
            idToken,
          }),
        },
      );
      return fallbackRes.ok;
    };

    const sendResetOob = async (): Promise<boolean> => {
      const withUrlRes = await fetch(
        `https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=${encodeURIComponent(apiKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requestType: "PASSWORD_RESET",
            email: normalizedEmail,
            continueUrl,
          }),
        },
      );
      if (withUrlRes.ok) return true;

      const fallbackRes = await fetch(
        `https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key=${encodeURIComponent(apiKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requestType: "PASSWORD_RESET",
            email: normalizedEmail,
          }),
        },
      );
      return fallbackRes.ok;
    };

    // 1. Try creating a provisional account via Identity Toolkit REST API (does not affect current logged-in session)
    // so Firebase Auth dispatches a real VERIFY_EMAIL invitation to the new user's inbox.
    const signUpRes = await fetch(
      `https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${encodeURIComponent(apiKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: normalizedEmail,
          password: tempPassword,
          displayName: inviteDisplayName.slice(0, 80),
          returnSecureToken: true,
        }),
      },
    );

    if (signUpRes.ok) {
      const signUpData = (await signUpRes.json()) as { idToken?: string };
      if (signUpData.idToken) {
        if (await sendVerifyOob(signUpData.idToken)) return true;
      }
      return await sendResetOob();
    } else {
      // 2. If account already exists (e.g. resending invite to new user or existing user):
      const signInRes = await fetch(
        `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${encodeURIComponent(apiKey)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: normalizedEmail,
            password: tempPassword,
            returnSecureToken: true,
          }),
        },
      );

      if (signInRes.ok) {
        const signInData = (await signInRes.json()) as { idToken?: string };
        if (signInData.idToken) {
          await fetch(
            `https://identitytoolkit.googleapis.com/v1/accounts:update?key=${encodeURIComponent(apiKey)}`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                idToken: signInData.idToken,
                displayName: inviteDisplayName.slice(0, 80),
              }),
            },
          ).catch(() => {});

          if (await sendVerifyOob(signInData.idToken)) return true;
        }
      }

      // 3. Fallback for already-registered users with custom passwords:
      return await sendResetOob();
    }
  } catch (err) {
    console.warn("Auto-email dispatch note:", err);
    return false;
  }
}

export async function ensureFriendInviteRecord(): Promise<{ code: string; link: string }> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const code = `friend_${user.uid}`;
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const link = `${origin}/join/${code}`;
  try {
    const myProfile = await getUserProfile(user.uid);
    const senderName =
      myProfile?.display_name || user.displayName || user.email || "Fair Share User";
    await setDoc(doc(db, "invitations", code), {
      id: code,
      type: "friend",
      code,
      sender_uid: user.uid,
      sender_name: senderName,
      created_at: new Date().toISOString(),
    });
  } catch {
    // Non-fatal if already exists
  }
  return { code, link };
}

export async function acceptFriendInviteByCode(codeRaw: string): Promise<{
  senderUid: string;
  senderName: string;
  alreadyFriends: boolean;
}> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");

  const code = codeRaw.trim();
  let senderUid = "";
  let senderName = "Friend";

  if (code.startsWith("friend_")) {
    senderUid = code.slice("friend_".length);
  } else {
    const invSnap = await getDoc(doc(db, "invitations", code));
    if (invSnap.exists() && invSnap.data().type === "friend") {
      senderUid = invSnap.data().sender_uid;
      senderName = invSnap.data().sender_name || "Friend";
    }
  }

  if (!senderUid) {
    throw new Error("Invalid friend invite link.");
  }
  if (senderUid === user.uid) {
    throw new Error("This is your own friend invite link.");
  }

  const senderProfile = await getUserProfile(senderUid);
  if (senderProfile?.display_name) {
    senderName = senderProfile.display_name;
  }

  const myProfile = await getUserProfile(user.uid);
  const myName = myProfile?.display_name || user.displayName || user.email || "Friend";
  const now = new Date().toISOString();

  // Check if a friendship doc already exists between these two users
  const fid = [senderUid, user.uid].sort().join("_");
  const fRef = doc(db, "friendships", fid);
  const fSnap = await getDoc(fRef);

  if (fSnap.exists()) {
    const existing = fSnap.data() as FriendshipDoc;
    if (
      existing.status === "accepted" &&
      existing.users.includes(user.uid) &&
      existing.users.includes(senderUid)
    ) {
      return { senderUid, senderName, alreadyFriends: true };
    }
    await updateDoc(fRef, {
      status: "accepted",
      receiver_id: user.uid,
      users: [senderUid, user.uid].sort(),
      updated_at: now,
    });
  } else {
    const newFriendship: FriendshipDoc = {
      id: fid,
      users: [senderUid, user.uid].sort(),
      sender_id: senderUid,
      receiver_id: user.uid,
      receiver_email: user.email?.toLowerCase() || null,
      status: "accepted",
      created_at: now,
      updated_at: now,
    };
    await setDoc(fRef, newFriendship);
  }

  // Also check if there were any pending email-based friendship docs from senderUid and mark them accepted/cleaned
  try {
    const qPending = query(
      collection(db, "friendships"),
      where("users", "array-contains", senderUid),
    );
    const pSnap = await getDocs(qPending);
    for (const d of pSnap.docs) {
      const fd = d.data() as FriendshipDoc;
      if (
        fd.id !== fid &&
        fd.status === "pending" &&
        ((user.email && fd.receiver_email?.toLowerCase() === user.email.toLowerCase()) ||
          fd.receiver_id === user.uid)
      ) {
        await deleteDoc(doc(db, "friendships", fd.id));
      }
    }
  } catch {
    // Non-fatal
  }

  // Notify the inviter that they are now connected as friends
  try {
    const notifId = generateToken(16);
    await setDoc(doc(db, "notifications", notifId), {
      id: notifId,
      recipient_uid: senderUid,
      sender_uid: user.uid,
      sender_name: myName,
      type: "friend_accepted",
      title: "New Friend Connected",
      message: `${myName} accepted your invite link! You can now split expenses and add each other to any group.`,
      target_type: "friend",
      target_id: fid,
      is_read: false,
      created_at: now,
    });
  } catch {
    // Non-fatal
  }

  return { senderUid, senderName, alreadyFriends: false };
}

export async function sendFriendInvitation(targetEmailOrCode: string): Promise<{
  ok: boolean;
  error?: string;
  registered?: boolean;
  email?: string;
  autoEmailSent?: boolean;
  senderName?: string;
}> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const myProfile = await getUserProfile(user.uid);
  const senderName = myProfile?.display_name || user.displayName || user.email || "Friend";

  const targetInput = targetEmailOrCode.trim().toLowerCase();
  if (!targetInput) return { ok: false, error: "Please enter an email address" };
  if (!/^\S+@\S+\.\S+$/.test(targetInput)) {
    return { ok: false, error: "Please enter a valid email address" };
  }

  if (targetInput === user.email?.trim().toLowerCase()) {
    return { ok: false, error: "You cannot invite yourself" };
  }

  try {
    // Check if target is a registered user by email
    const usersQ = query(collection(db, "users"), where("email", "==", targetInput), limit(1));
    const userSnap = await getDocs(usersQ);
    let targetUid: string | null = null;
    let targetEmail: string = targetInput;

    if (!userSnap.empty) {
      targetUid = userSnap.docs[0]!.id;
      targetEmail = (userSnap.docs[0]!.data().email || targetInput).toLowerCase();
    }

    if (targetUid === user.uid) {
      return { ok: false, error: "You cannot add yourself as a friend" };
    }

    // Check existing friendships involving current user via safe list query
    const myFriendsQ = query(
      collection(db, "friendships"),
      where("users", "array-contains", user.uid),
    );
    const myFriendsSnap = await getDocs(myFriendsQ);
    const existingDoc = myFriendsSnap.docs
      .map((d) => d.data() as FriendshipDoc)
      .find(
        (f) =>
          (targetUid && f.users.includes(targetUid)) ||
          (f.receiver_email && f.receiver_email.toLowerCase() === targetEmail),
      );

    const origin =
      typeof window !== "undefined" ? window.location.origin : "https://fairshare-rm.ai.studio";
    const friendInviteCode = `friend_${user.uid}`;
    const inviteUrl = `${origin}/join/${friendInviteCode}`;

    if (existingDoc) {
      if (existingDoc.status === "accepted") {
        return { ok: false, error: "You are already friends with this person" };
      }
      if (existingDoc.status === "pending") {
        const autoEmailSent = await sendAutoGeneratedInviteEmail({
          recipientEmail: targetEmail,
          senderName,
          inviteUrl,
        });
        return {
          ok: true,
          registered: !!targetUid,
          email: targetEmail,
          autoEmailSent,
          senderName,
        };
      }
    }

    const fid = existingDoc?.id
      ? existingDoc.id
      : targetUid
        ? [user.uid, targetUid].sort().join("_")
        : `email_${generateToken(12)}`;

    const now = new Date().toISOString();
    const friendship: FriendshipDoc = {
      id: fid,
      users: targetUid ? [user.uid, targetUid].sort() : [user.uid],
      sender_id: user.uid,
      receiver_id: targetUid,
      receiver_email: targetEmail,
      status: "pending",
      created_at: now,
      updated_at: now,
    };

    await setDoc(doc(db, "friendships", fid), friendship);

    // Ensure the user's friend invite code doc exists
    await setDoc(doc(db, "invitations", friendInviteCode), {
      id: friendInviteCode,
      type: "friend",
      code: friendInviteCode,
      sender_uid: user.uid,
      sender_name: senderName,
      created_at: now,
    });

    // If target is registered, send in-app notification
    if (targetUid) {
      const notifId = generateToken(16);
      await setDoc(doc(db, "notifications", notifId), {
        id: notifId,
        recipient_uid: targetUid,
        sender_uid: user.uid,
        sender_name: senderName,
        type: "friend_request",
        title: "New Friend Request",
        message: `${senderName} invited you to connect on Fair Share.`,
        target_type: "friend",
        target_id: fid,
        is_read: false,
        created_at: now,
      });
    }

    // Automatically send auto-generated email from Fair Share
    const autoEmailSent = await sendAutoGeneratedInviteEmail({
      recipientEmail: targetEmail,
      senderName,
      inviteUrl,
    });

    return { ok: true, registered: !!targetUid, email: targetEmail, autoEmailSent, senderName };
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, "friendships");
  }
}

export async function respondToFriendRequest(friendshipId: string, accept: boolean): Promise<void> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const fRef = doc(db, "friendships", friendshipId);
  try {
    const snap = await getDoc(fRef);
    if (!snap.exists()) throw new Error("Friend request not found");
    const data = snap.data() as FriendshipDoc;
    const now = new Date().toISOString();

    if (accept) {
      const users = Array.from(new Set([...data.users, user.uid])).sort();
      await updateDoc(fRef, {
        status: "accepted",
        receiver_id: user.uid,
        users,
        updated_at: now,
      });

      // Notify sender
      const myProfile = await getUserProfile(user.uid);
      const myName = myProfile?.display_name || user.email || "Friend";
      const notifId = generateToken(16);
      await setDoc(doc(db, "notifications", notifId), {
        id: notifId,
        recipient_uid: data.sender_id,
        sender_uid: user.uid,
        sender_name: myName,
        type: "friend_accepted",
        title: "Friend Request Accepted",
        message: `${myName} accepted your friend request!`,
        target_type: "friend",
        target_id: friendshipId,
        is_read: false,
        created_at: now,
      });
    } else {
      await updateDoc(fRef, { status: "declined", updated_at: now });
    }
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, `friendships/${friendshipId}`);
  }
}

export async function listUserFriendships(uid: string): Promise<FriendshipDoc[]> {
  try {
    const q1 = query(collection(db, "friendships"), where("users", "array-contains", uid));
    const snap = await getDocs(q1);
    return snap.docs.map((d) => d.data() as FriendshipDoc);
  } catch (err) {
    handleFirestoreError(err, OperationType.LIST, "friendships");
  }
}

// -------------------------------------------------------------
// GROUPS & MEMBERS
// -------------------------------------------------------------

export async function createGroup(
  name: string,
  category: string,
  currency: string,
  initialFriendUids: string[] = [],
): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const myProfile = await getUserProfile(user.uid);
  const myName = myProfile?.display_name || user.email || "Me";

  const groupId = generateToken(16);
  const memberId = generateToken(16);
  const inviteCode = generateToken(8);
  const now = new Date().toISOString();

  const extraUids = Array.from(new Set(initialFriendUids.filter((id) => id && id !== user.uid)));
  const allMemberUids = [user.uid, ...extraUids];

  const group: GroupDoc = {
    id: groupId,
    name: name.trim(),
    category: category as GroupDoc["category"],
    currency: currency.toUpperCase(),
    invite_code: inviteCode,
    created_by: user.uid,
    member_ids: allMemberUids,
    archived_at: null,
    created_at: now,
    updated_at: now,
  };

  const member: GroupMemberDoc = {
    id: memberId,
    group_id: groupId,
    user_id: user.uid,
    name: myName,
    email: user.email ?? null,
    avatar_url: myProfile?.avatar_url ?? null,
    role: "admin",
    claim_token: null,
    claim_token_expires_at: null,
    joined_at: now,
  };

  try {
    const friendProfiles = await Promise.all(extraUids.map((fUid) => getUserProfile(fUid)));
    const batch = writeBatch(db);
    batch.set(doc(db, "groups", groupId), group);
    batch.set(doc(db, "groups", groupId, "members", memberId), member);

    // Add any selected initial friends as group members and notify them
    extraUids.forEach((fUid, idx) => {
      const fp = friendProfiles[idx];
      const fMemberId = generateToken(16);
      const fName = fp?.display_name || fp?.email?.split("@")[0] || "Friend";
      const fMember: GroupMemberDoc = {
        id: fMemberId,
        group_id: groupId,
        user_id: fUid,
        name: fName,
        email: fp?.email ?? null,
        avatar_url: fp?.avatar_url ?? null,
        role: "member",
        claim_token: null,
        claim_token_expires_at: null,
        joined_at: now,
      };
      batch.set(doc(db, "groups", groupId, "members", fMemberId), fMember);

      const notifId = generateToken(16);
      batch.set(doc(db, "notifications", notifId), {
        id: notifId,
        recipient_uid: fUid,
        sender_uid: user.uid,
        sender_name: myName,
        type: "friend_request",
        title: `Added to "${group.name}"`,
        message: `${myName} created the group "${group.name}" with you.`,
        target_type: "group",
        target_id: groupId,
        is_read: false,
        created_at: now,
      });
    });

    // Also write invitation lookup
    batch.set(doc(db, "invitations", inviteCode), {
      id: inviteCode,
      type: "group",
      code: inviteCode,
      group_id: groupId,
      sender_uid: user.uid,
      sender_name: myName,
      created_at: now,
    });

    // Activity
    const actId = generateToken(16);
    batch.set(doc(db, "activity", actId), {
      id: actId,
      group_id: groupId,
      participant_uids: allMemberUids,
      actor_uid: user.uid,
      actor_name: myName,
      action: "create_group",
      description: `Created group "${name}"`,
      currency,
      amount_units: null,
      created_at: now,
    });

    await batch.commit();
    return groupId;
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, `groups/${groupId}`);
  }
}

export async function addPlaceholderMember(groupId: string, name: string): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const memberId = generateToken(16);
  const now = new Date().toISOString();

  const member: GroupMemberDoc = {
    id: memberId,
    group_id: groupId,
    user_id: null,
    name: name.trim(),
    email: null,
    avatar_url: null,
    role: "member",
    claim_token: null,
    claim_token_expires_at: null,
    joined_at: now,
  };

  try {
    await setDoc(doc(db, "groups", groupId, "members", memberId), member);
    return memberId;
  } catch (err) {
    handleFirestoreError(err, OperationType.CREATE, `groups/${groupId}/members/${memberId}`);
  }
}

export async function addFriendToGroup(
  groupId: string,
  friendUid: string,
): Promise<{ ok: boolean; error?: string; friendName?: string }> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  try {
    const myProfile = await getUserProfile(user.uid);
    const senderName =
      myProfile?.display_name || user.displayName || user.email || "A group member";

    const groupRef = doc(db, "groups", groupId);
    const groupSnap = await getDoc(groupRef);
    if (!groupSnap.exists()) return { ok: false, error: "Group not found" };
    const groupData = groupSnap.data() as GroupDoc;

    const membersSnap = await getDocs(collection(db, "groups", groupId, "members"));
    const members = membersSnap.docs.map((d) => d.data() as GroupMemberDoc);
    if (members.some((m) => m.user_id === friendUid)) {
      return { ok: false, error: "This friend is already in the group" };
    }

    const friendProfile = await getUserProfile(friendUid);
    const friendName =
      friendProfile?.display_name || friendProfile?.email?.split("@")[0] || "Friend";
    const friendEmail = friendProfile?.email || null;
    const now = new Date().toISOString();
    const memberId = generateToken(16);

    const newMember: GroupMemberDoc = {
      id: memberId,
      group_id: groupId,
      user_id: friendUid,
      name: friendName,
      email: friendEmail,
      avatar_url: friendProfile?.avatar_url || null,
      role: "member",
      claim_token: null,
      claim_token_expires_at: null,
      joined_at: now,
    };

    const batch = writeBatch(db);
    batch.set(doc(db, "groups", groupId, "members", memberId), newMember);
    batch.update(groupRef, {
      member_ids: Array.from(new Set([...(groupData.member_ids ?? []), friendUid])),
      updated_at: now,
    });

    const notifId = generateToken(16);
    batch.set(doc(db, "notifications", notifId), {
      id: notifId,
      recipient_uid: friendUid,
      sender_uid: user.uid,
      sender_name: senderName,
      type: "friend_request",
      title: `Added to "${groupData.name}"`,
      message: `${senderName} added you to the group "${groupData.name}".`,
      target_type: "group",
      target_id: groupId,
      is_read: false,
      created_at: now,
    });

    await batch.commit();
    return { ok: true, friendName };
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, `groups/${groupId}/members`);
  }
}

export async function inviteMemberByEmailToGroup(
  groupId: string,
  groupName: string,
  inviteCode: string,
  targetEmailRaw: string,
): Promise<{
  ok: boolean;
  error?: string;
  registered?: boolean;
  claimToken?: string;
  autoEmailSent?: boolean;
}> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const normalizedEmail = targetEmailRaw.trim().toLowerCase();
  if (!normalizedEmail || !/^\S+@\S+\.\S+$/.test(normalizedEmail)) {
    return { ok: false, error: "Please enter a valid email address" };
  }

  try {
    const myProfile = await getUserProfile(user.uid);
    const senderName =
      myProfile?.display_name || user.displayName || user.email || "A group member";
    const origin =
      typeof window !== "undefined" ? window.location.origin : "https://fairshare-rm.ai.studio";

    // Check existing group members
    const membersSnap = await getDocs(collection(db, "groups", groupId, "members"));
    const members = membersSnap.docs.map((d) => d.data() as GroupMemberDoc);
    if (members.some((m) => m.email?.toLowerCase() === normalizedEmail)) {
      return { ok: false, error: "This email is already added to the group" };
    }

    // Check if user is registered
    const usersQ = query(collection(db, "users"), where("email", "==", normalizedEmail), limit(1));
    const userSnap = await getDocs(usersQ);
    const now = new Date().toISOString();
    const token = generateToken(32);
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

    if (!userSnap.empty) {
      const targetUser = userSnap.docs[0]!.data() as UserProfile;
      if (members.some((m) => m.user_id === targetUser.id)) {
        return { ok: false, error: "This user is already a member of the group" };
      }

      const memberId = generateToken(16);
      const newMember: GroupMemberDoc = {
        id: memberId,
        group_id: groupId,
        user_id: targetUser.id,
        name: targetUser.display_name || normalizedEmail.split("@")[0] || "Member",
        email: normalizedEmail,
        avatar_url: targetUser.avatar_url || null,
        role: "member",
        claim_token: null,
        claim_token_expires_at: null,
        joined_at: now,
      };

      const groupRef = doc(db, "groups", groupId);
      const groupSnap = await getDoc(groupRef);
      const currentMemberIds = groupSnap.exists()
        ? ((groupSnap.data() as GroupDoc).member_ids ?? [])
        : [user.uid];

      const batch = writeBatch(db);
      batch.set(doc(db, "groups", groupId, "members", memberId), newMember);
      batch.update(groupRef, {
        member_ids: Array.from(new Set([...currentMemberIds, targetUser.id])),
        updated_at: now,
      });

      const notifId = generateToken(16);
      batch.set(doc(db, "notifications", notifId), {
        id: notifId,
        recipient_uid: targetUser.id,
        sender_uid: user.uid,
        sender_name: senderName,
        type: "friend_request",
        title: `Added to "${groupName}"`,
        message: `${senderName} added you to the group "${groupName}".`,
        target_type: "group",
        target_id: groupId,
        is_read: false,
        created_at: now,
      });

      await batch.commit();

      const autoEmailSent = await sendAutoGeneratedInviteEmail({
        recipientEmail: normalizedEmail,
        senderName,
        inviteUrl: `${origin}/join/${inviteCode}`,
        groupName,
      });

      return { ok: true, registered: true, autoEmailSent };
    } else {
      // Unregistered email: create placeholder member with email & claim token
      const memberId = generateToken(16);
      const fallbackName = normalizedEmail.split("@")[0] || "Invited Member";
      const member: GroupMemberDoc = {
        id: memberId,
        group_id: groupId,
        user_id: null,
        name: fallbackName,
        email: normalizedEmail,
        avatar_url: null,
        role: "member",
        claim_token: token,
        claim_token_expires_at: expiresAt,
        joined_at: now,
      };
      await setDoc(doc(db, "groups", groupId, "members", memberId), member);

      // Record group email invitation so if the user signs up with this email directly, they are auto-added to the group
      const invId = `gemail_${groupId}_${generateToken(8)}`;
      await setDoc(doc(db, "invitations", invId), {
        id: invId,
        type: "group_email",
        code: inviteCode,
        group_id: groupId,
        member_id: memberId,
        receiver_email: normalizedEmail,
        sender_uid: user.uid,
        sender_name: senderName,
        created_at: now,
      });

      const autoEmailSent = await sendAutoGeneratedInviteEmail({
        recipientEmail: normalizedEmail,
        senderName,
        inviteUrl: `${origin}/join/${inviteCode}?claim=${encodeURIComponent(token)}`,
        groupName,
      });

      return { ok: true, registered: false, claimToken: token, autoEmailSent };
    }
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, `groups/${groupId}/members`);
  }
}

export async function createClaimLink(groupId: string, memberId: string): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const token = generateToken(32);
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

  try {
    const mRef = doc(db, "groups", groupId, "members", memberId);
    await updateDoc(mRef, {
      claim_token: token,
      claim_token_expires_at: expiresAt,
    });
    return token;
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, `groups/${groupId}/members/${memberId}`);
  }
}

export async function joinGroup(code: string, claimToken?: string): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const myProfile = await getUserProfile(user.uid);
  const myName = myProfile?.display_name || user.email || "Member";

  try {
    // Find group by invite code
    const groupsQ = query(
      collection(db, "groups"),
      where("invite_code", "==", code.trim()),
      limit(1),
    );
    const snap = await getDocs(groupsQ);
    if (snap.empty) throw new Error("This invite link is invalid or has expired.");
    const group = snap.docs[0]!.data() as GroupDoc;

    if (group.archived_at) throw new Error("This group is archived and not accepting new members.");

    // Check if already in group
    const membersSnap = await getDocs(collection(db, "groups", group.id, "members"));
    const members = membersSnap.docs.map((d) => d.data() as GroupMemberDoc);

    const existingMember = members.find((m) => m.user_id === user.uid);
    if (existingMember) return group.id;

    const now = new Date().toISOString();

    // Check claim token
    if (claimToken && claimToken.trim()) {
      const target = members.find(
        (m) =>
          m.claim_token === claimToken.trim() &&
          !m.user_id &&
          m.claim_token_expires_at &&
          new Date(m.claim_token_expires_at).getTime() > Date.now(),
      );
      if (!target) {
        throw new Error("This claim link is invalid, expired, or has already been used.");
      }

      const batch = writeBatch(db);
      batch.update(doc(db, "groups", group.id, "members", target.id), {
        user_id: user.uid,
        email: user.email ?? null,
        avatar_url: myProfile?.avatar_url ?? null,
        claim_token: null,
        claim_token_expires_at: null,
      });
      batch.update(doc(db, "groups", group.id), {
        member_ids: Array.from(new Set([...group.member_ids, user.uid])),
        updated_at: now,
      });
      await batch.commit();
      return group.id;
    }

    // Standard join
    const newMemberId = generateToken(16);
    const newMember: GroupMemberDoc = {
      id: newMemberId,
      group_id: group.id,
      user_id: user.uid,
      name: myName,
      email: user.email ?? null,
      avatar_url: myProfile?.avatar_url ?? null,
      role: "member",
      claim_token: null,
      claim_token_expires_at: null,
      joined_at: now,
    };

    const batch = writeBatch(db);
    batch.set(doc(db, "groups", group.id, "members", newMemberId), newMember);
    batch.update(doc(db, "groups", group.id), {
      member_ids: Array.from(new Set([...group.member_ids, user.uid])),
      updated_at: now,
    });
    await batch.commit();
    return group.id;
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, "groups/join");
  }
}

// -------------------------------------------------------------
// EXPENSES & SETTLEMENTS (GROUP & DIRECT)
// -------------------------------------------------------------

export async function saveExpense(params: {
  expenseId?: string | null;
  groupId?: string | null;
  friendshipId?: string | null;
  description: string;
  amount_units: number;
  currency: string;
  category: string;
  paid_by_member_id?: string | null;
  paid_by_uid: string;
  split_type: "EQUAL" | "EXACT" | "PERCENTAGE";
  expense_date: string;
  splits: ExpenseSplit[];
  note?: string | null;
  participant_uids: string[];
}): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");

  if (!params.description.trim()) throw new Error("Description is required");
  if (params.amount_units <= 0) throw new Error("Amount must be greater than zero");

  const totalSplits = params.splits.reduce((s, x) => s + x.amount_units, 0);
  if (totalSplits !== params.amount_units) {
    throw new Error(`Splits sum (${totalSplits}) must equal total amount (${params.amount_units})`);
  }

  const eid = params.expenseId || generateToken(16);
  const now = new Date().toISOString();
  const participantUids = Array.from(new Set([...params.participant_uids, user.uid])).filter(
    Boolean,
  );

  try {
    const batch = writeBatch(db);
    if (params.expenseId) {
      batch.update(doc(db, "expenses", eid), {
        participant_uids: participantUids,
        description: params.description.trim(),
        amount_units: params.amount_units,
        currency: params.currency.toUpperCase(),
        category: params.category,
        paid_by_member_id: params.paid_by_member_id ?? null,
        paid_by_uid: params.paid_by_uid,
        split_type: params.split_type,
        expense_date: params.expense_date,
        note: params.note?.trim() || null,
        splits: params.splits,
        updated_at: now,
      });
    } else {
      const docData: ExpenseDoc = {
        id: eid,
        group_id: params.groupId ?? null,
        friendship_id: params.friendshipId ?? null,
        participant_uids: participantUids,
        description: params.description.trim(),
        amount_units: params.amount_units,
        currency: params.currency.toUpperCase(),
        category: params.category,
        paid_by_member_id: params.paid_by_member_id ?? null,
        paid_by_uid: params.paid_by_uid,
        split_type: params.split_type,
        expense_date: params.expense_date,
        note: params.note?.trim() || null,
        created_by: user.uid,
        splits: params.splits,
        created_at: now,
        updated_at: now,
      };
      batch.set(doc(db, "expenses", eid), docData);
    }

    const actId = generateToken(16);
    batch.set(doc(db, "activity", actId), {
      id: actId,
      group_id: params.groupId ?? null,
      friendship_id: params.friendshipId ?? null,
      participant_uids: participantUids,
      actor_uid: user.uid,
      actor_name: user.displayName || user.email || "Member",
      action: params.expenseId ? "update_expense" : "create_expense",
      description: `${params.expenseId ? "Updated" : "Added"} expense: ${params.description} (${formatMoney(params.amount_units, params.currency)})`,
      currency: params.currency,
      amount_units: params.amount_units,
      created_at: now,
    });

    await batch.commit();
    return eid;
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, `expenses/${eid}`);
  }
}

export async function deleteExpense(expenseId: string): Promise<void> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const eRef = doc(db, "expenses", expenseId);
  try {
    const snap = await getDoc(eRef);
    if (!snap.exists()) return;
    const data = snap.data() as ExpenseDoc;

    const batch = writeBatch(db);
    batch.delete(eRef);

    const actId = generateToken(16);
    batch.set(doc(db, "activity", actId), {
      id: actId,
      group_id: data.group_id ?? null,
      friendship_id: data.friendship_id ?? null,
      participant_uids: Array.from(new Set([...(data.participant_uids ?? []), user.uid])),
      actor_uid: user.uid,
      actor_name: user.displayName || user.email || "Member",
      action: "delete_expense",
      description: `Deleted expense: ${data.description}`,
      currency: data.currency,
      amount_units: data.amount_units,
      created_at: new Date().toISOString(),
    });

    await batch.commit();
  } catch (err) {
    handleFirestoreError(err, OperationType.DELETE, `expenses/${expenseId}`);
  }
}

export async function saveSettlement(params: {
  settlementId?: string | null;
  groupId?: string | null;
  friendshipId?: string | null;
  from_member_id?: string | null;
  to_member_id?: string | null;
  from_uid: string;
  to_uid: string;
  amount_units: number;
  currency: string;
  settled_on: string;
  note?: string | null;
}): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  if (params.from_uid === params.to_uid)
    throw new Error("Payer and recipient cannot be the same person");
  if (params.amount_units <= 0) throw new Error("Amount must be positive");

  const sid = params.settlementId || generateToken(16);
  const now = new Date().toISOString();
  const participantUids = Array.from(
    new Set([params.from_uid, params.to_uid, user.uid]),
  ).filter(Boolean);

  try {
    const batch = writeBatch(db);
    if (params.settlementId) {
      batch.update(doc(db, "settlements", sid), {
        participant_uids: participantUids,
        from_member_id: params.from_member_id ?? null,
        to_member_id: params.to_member_id ?? null,
        from_uid: params.from_uid,
        to_uid: params.to_uid,
        amount_units: params.amount_units,
        currency: params.currency.toUpperCase(),
        settled_on: params.settled_on,
        note: params.note?.trim() || null,
      });
    } else {
      const docData: SettlementDoc = {
        id: sid,
        group_id: params.groupId ?? null,
        friendship_id: params.friendshipId ?? null,
        participant_uids: participantUids,
        from_member_id: params.from_member_id ?? null,
        to_member_id: params.to_member_id ?? null,
        from_uid: params.from_uid,
        to_uid: params.to_uid,
        amount_units: params.amount_units,
        currency: params.currency.toUpperCase(),
        settled_on: params.settled_on,
        note: params.note?.trim() || null,
        created_by: user.uid,
        created_at: now,
      };
      batch.set(doc(db, "settlements", sid), docData);
    }

    const actId = generateToken(16);
    batch.set(doc(db, "activity", actId), {
      id: actId,
      group_id: params.groupId ?? null,
      friendship_id: params.friendshipId ?? null,
      participant_uids: participantUids,
      actor_uid: user.uid,
      actor_name: user.displayName || user.email || "Member",
      action: params.settlementId ? "update_settlement" : "record_settlement",
      description: `Payment recorded: ${formatMoney(params.amount_units, params.currency)}`,
      currency: params.currency,
      amount_units: params.amount_units,
      created_at: now,
    });

    await batch.commit();
    return sid;
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, `settlements/${sid}`);
  }
}

export async function deleteSettlement(settlementId: string): Promise<void> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const sRef = doc(db, "settlements", settlementId);
  try {
    const snap = await getDoc(sRef);
    if (!snap.exists()) return;
    const data = snap.data() as SettlementDoc;

    const batch = writeBatch(db);
    batch.delete(sRef);

    const actId = generateToken(16);
    batch.set(doc(db, "activity", actId), {
      id: actId,
      group_id: data.group_id ?? null,
      friendship_id: data.friendshipId ?? null,
      participant_uids: data.participant_uids,
      actor_uid: user.uid,
      actor_name: user.displayName || user.email || "Member",
      action: "delete_settlement",
      description: `Deleted payment of ${formatMoney(data.amount_units, data.currency)}`,
      currency: data.currency,
      amount_units: data.amount_units,
      created_at: new Date().toISOString(),
    });

    await batch.commit();
  } catch (err) {
    handleFirestoreError(err, OperationType.DELETE, `settlements/${settlementId}`);
  }
}

// -------------------------------------------------------------
// REMINDERS & NOTIFICATIONS (RATE-LIMITED)
// -------------------------------------------------------------

export async function sendBalanceReminder(params: {
  recipient_uid: string;
  currency: string;
  amount_units: number;
  target_type: "group" | "friend";
  target_id: string;
  title?: string;
}): Promise<{ ok: boolean; error?: string }> {
  const user = auth.currentUser;
  if (!user) throw new Error("Please sign in first");
  const myProfile = await getUserProfile(user.uid);
  const myName = myProfile?.display_name || user.email || "Friend";

  try {
    // Rate limit check: has this user sent a reminder to this recipient in the last 1 hour?
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const q1 = query(
      collection(db, "notifications"),
      where("recipient_uid", "==", params.recipient_uid),
      where("sender_uid", "==", user.uid),
      where("type", "==", "reminder"),
    );
    const existing = await getDocs(q1);
    const recent = existing.docs.some((d) => d.data().created_at > oneHourAgo);
    if (recent) {
      return {
        ok: false,
        error:
          "A reminder was already sent to this person recently. Please wait before sending another.",
      };
    }

    const notifId = generateToken(16);
    const now = new Date().toISOString();
    const moneyStr = formatMoney(params.amount_units, params.currency);

    await setDoc(doc(db, "notifications", notifId), {
      id: notifId,
      recipient_uid: params.recipient_uid,
      sender_uid: user.uid,
      sender_name: myName,
      type: "reminder",
      title: params.title || "Friendly balance reminder",
      message: `${myName} sent you a reminder for ${moneyStr}.`,
      target_type: params.target_type,
      target_id: params.target_id,
      currency: params.currency,
      amount_units: params.amount_units,
      is_read: false,
      created_at: now,
    });

    return { ok: true };
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, "notifications");
  }
}

export async function markNotificationAsRead(notifId: string): Promise<void> {
  try {
    await updateDoc(doc(db, "notifications", notifId), { is_read: true });
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, `notifications/${notifId}`);
  }
}

export async function markAllNotificationsAsRead(notifIds: string[]): Promise<void> {
  if (!notifIds.length) return;
  try {
    const batch = writeBatch(db);
    for (const id of notifIds) {
      batch.update(doc(db, "notifications", id), { is_read: true });
    }
    await batch.commit();
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, "notifications/batch");
  }
}

export async function listUserNotifications(uid: string): Promise<NotificationDoc[]> {
  try {
    const q1 = query(collection(db, "notifications"), where("recipient_uid", "==", uid));
    const snap = await getDocs(q1);
    return snap.docs
      .map((d) => d.data() as NotificationDoc)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, 50);
  } catch (err) {
    handleFirestoreError(err, OperationType.LIST, "notifications");
  }
}

// -------------------------------------------------------------
// ACCOUNT CLOSING (ZERO-BALANCE VERIFICATION)
// -------------------------------------------------------------

export async function checkCanCloseAccount(uid: string): Promise<{
  canClose: boolean;
  blockingBalances: Array<{ label: string; currency: string; netUnits: number }>;
}> {
  try {
    // 1. Fetch all expenses where user is a participant
    const expQ = query(
      collection(db, "expenses"),
      where("participant_uids", "array-contains", uid),
    );
    const expSnap = await getDocs(expQ);
    const expenses = expSnap.docs.map((d) => d.data() as ExpenseDoc);

    // 2. Fetch all settlements where user is a participant
    const setQ = query(
      collection(db, "settlements"),
      where("participant_uids", "array-contains", uid),
    );
    const setSnap = await getDocs(setQ);
    const settlements = setSnap.docs.map((d) => d.data() as SettlementDoc);

    // Group by currency and counterparty or group
    const balancesByCurr: Record<string, number> = {};

    for (const e of expenses) {
      const curr = e.currency;
      if (e.paid_by_uid === uid) {
        // I paid -> I am credited for what others owe
        for (const s of e.splits) {
          if (s.user_id !== uid) {
            balancesByCurr[curr] = (balancesByCurr[curr] ?? 0) + s.amount_units;
          }
        }
      } else {
        // Someone else paid -> I owe my share
        const myShare = e.splits.find((s) => s.user_id === uid)?.amount_units ?? 0;
        balancesByCurr[curr] = (balancesByCurr[curr] ?? 0) - myShare;
      }
    }

    for (const s of settlements) {
      const curr = s.currency;
      if (s.from_uid === uid) {
        // I paid settlement -> reduces debt / increases credit
        balancesByCurr[curr] = (balancesByCurr[curr] ?? 0) + s.amount_units;
      } else if (s.to_uid === uid) {
        // I received settlement -> reduces credit
        balancesByCurr[curr] = (balancesByCurr[curr] ?? 0) - s.amount_units;
      }
    }

    const blockingBalances = Object.entries(balancesByCurr)
      .filter(([, net]) => net !== 0)
      .map(([curr, net]) => ({
        label: net > 0 ? "You are owed" : "You owe",
        currency: curr,
        netUnits: Math.abs(net),
      }));

    return {
      canClose: blockingBalances.length === 0,
      blockingBalances,
    };
  } catch (err) {
    handleFirestoreError(err, OperationType.GET, "checkCloseAccount");
  }
}

export async function closeAccount(uid: string): Promise<void> {
  const check = await checkCanCloseAccount(uid);
  if (!check.canClose) {
    throw new Error(
      `Cannot close account with outstanding balances: ${check.blockingBalances
        .map((b) => `${b.label} ${formatMoney(b.netUnits, b.currency)}`)
        .join(", ")}`,
    );
  }

  try {
    const myProfile = await getUserProfile(uid);
    const formerName =
      myProfile?.display_name ||
      auth.currentUser?.displayName ||
      auth.currentUser?.email ||
      "A member";

    const batch = writeBatch(db);
    const now = new Date().toISOString();

    // 1. Delete all friendships involving this user so their name disappears from Friends lists
    const fQ = query(collection(db, "friendships"), where("users", "array-contains", uid));
    const fSnap = await getDocs(fQ);
    for (const fd of fSnap.docs) {
      batch.delete(doc(db, "friendships", fd.id));
    }

    // 2. Notify all members who share a group with this user and unlink/anonymize membership
    const gQ = query(collection(db, "groups"), where("member_ids", "array-contains", uid));
    const gSnap = await getDocs(gQ);
    for (const gd of gSnap.docs) {
      const gData = gd.data() as GroupDoc;
      const membersSnap = await getDocs(collection(db, "groups", gd.id, "members"));
      const memberDocUids = membersSnap.docs
        .map((md) => (md.data() as GroupMemberDoc).user_id)
        .filter((id): id is string => !!id);
      const otherMemberUids = Array.from(
        new Set([...(gData.member_ids ?? []), ...memberDocUids]),
      ).filter((id) => id !== uid);

      // Notify every other member in the group
      for (const recipientUid of otherMemberUids) {
        const notifId = generateToken(16);
        batch.set(doc(db, "notifications", notifId), {
          id: notifId,
          recipient_uid: recipientUid,
          sender_uid: uid,
          sender_name: formerName,
          type: "reminder",
          title: `Member deleted account in "${gData.name}"`,
          message: `${formerName} has deleted their Fair Share account and is no longer an active member of "${gData.name}".`,
          target_type: "group",
          target_id: gd.id,
          is_read: false,
          created_at: now,
        });
      }

      // Record group activity
      if (otherMemberUids.length > 0) {
        const actId = generateToken(16);
        batch.set(doc(db, "activity", actId), {
          id: actId,
          group_id: gd.id,
          friendship_id: null,
          participant_uids: Array.from(new Set([uid, ...otherMemberUids])),
          actor_uid: uid,
          actor_name: formerName,
          action: "member_deleted_account",
          description: `${formerName} deleted their Fair Share account (in "${gData.name}")`,
          currency: null,
          amount_units: null,
          created_at: now,
        });
      }

      for (const md of membersSnap.docs) {
        if (md.data().user_id === uid) {
          batch.update(doc(db, "groups", gd.id, "members", md.id), {
            user_id: null,
            name: `${formerName} (Deleted)`,
            email: null,
            avatar_url: null,
          });
        }
      }

      batch.update(doc(db, "groups", gd.id), {
        member_ids: otherMemberUids,
        updated_at: now,
      });
    }

    // 3. Anonymize user profile
    batch.update(doc(db, "users", uid), {
      display_name: "Deleted user",
      phone_number: null,
      avatar_url: null,
      push_tokens: [],
      is_deleted: true,
      updated_at: now,
    });

    await batch.commit();

    // 4. Delete from Firebase Auth
    if (auth.currentUser && auth.currentUser.uid === uid) {
      try {
        await auth.currentUser.delete();
      } catch {
        // If session is older than 5 minutes (requires-recent-login), sign out cleanly since data is anonymized
        await signOut(auth);
      }
    }
  } catch (err) {
    handleFirestoreError(err, OperationType.DELETE, `users/${uid}`);
  }
}
