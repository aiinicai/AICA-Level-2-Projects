import React, { useState, useEffect, useRef } from "react";
import { db } from "../lib/firebase";
import {
  doc,
  onSnapshot,
  updateDoc,
  collection,
  addDoc,
  serverTimestamp,
  query,
  orderBy,
  where
} from "firebase/firestore";
import { Engagement, Client, Service, EngagementDocument, UserProfile, ClientComment, PendingItem, ReviewNote } from "../types";
import { SERVICES_CONFIG } from "../lib/retention";
import {
  FolderOpen,
  ArrowLeft,
  Send,
  Lock,
  Unlock,
  CheckCircle,
  Clock,
  RotateCcw,
  FileText,
  Upload,
  Calendar,
  AlertOctagon,
  ShieldAlert,
  ShieldCheck,
  XCircle,
  FileCheck,
  UserCheck,
  AlertTriangle,
  Users,
  UserPlus,
  FileUp,
  Paperclip,
  CheckCircle2,
  Trash2,
  Download,
  MessageSquare,
  MessageCircle,
  CornerDownRight,
  ListTodo,
  AlertCircle,
  CheckSquare
} from "lucide-react";

interface EngagementDetailViewProps {
  engagementId: string;
  userProfile: UserProfile;
  onBack: () => void;
}

export const EngagementDetailView: React.FC<EngagementDetailViewProps> = ({
  engagementId,
  userProfile,
  onBack
}) => {
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [service, setService] = useState<Service | null>(null);
  const [documents, setDocuments] = useState<EngagementDocument[]>([]);
  const [teamMembers, setTeamMembers] = useState<UserProfile[]>([]);
  const [allUsersMap, setAllUsersMap] = useState<Record<string, UserProfile>>({});
  const [loading, setLoading] = useState(true);

  // Workflow Action States
  const [sendNote, setSendNote] = useState("");
  const [isSendBackOpen, setIsSendBackOpen] = useState(false);
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [selectedAssigneeIds, setSelectedAssigneeIds] = useState<string[]>([]);
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailProof, setEmailProof] = useState<any | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Document Upload State & Ref
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);
  const [updatingConsent, setUpdatingConsent] = useState(false);

  // Client Comments State (One-Way Client Response Channel)
  const [comments, setComments] = useState<ClientComment[]>([]);
  const [commentText, setCommentText] = useState("");
  const [postingComment, setPostingComment] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);
  const [commentSuccessMsg, setCommentSuccessMsg] = useState<string | null>(null);

  // Review Notes State (Internal Confidential Channel for full_admin & team_member ONLY)
  const [reviewNotes, setReviewNotes] = useState<ReviewNote[]>([]);
  const [reviewNoteText, setReviewNoteText] = useState("");
  const [postingReviewNote, setPostingReviewNote] = useState(false);
  const [reviewNoteError, setReviewNoteError] = useState<string | null>(null);
  const [reviewNoteSuccessMsg, setReviewNoteSuccessMsg] = useState<string | null>(null);

  // Pending Items State (Firm to Client Action Notices)
  const [pendingItems, setPendingItems] = useState<PendingItem[]>([]);
  const [pendingItemText, setPendingItemText] = useState("");
  const [postingPendingItem, setPostingPendingItem] = useState(false);
  const [resolvingItemId, setResolvingItemId] = useState<string | null>(null);
  const [pendingItemError, setPendingItemError] = useState<string | null>(null);
  const [pendingItemSuccessMsg, setPendingItemSuccessMsg] = useState<string | null>(null);

  // 1. Real-Time Engagement Listener
  useEffect(() => {
    setLoading(true);
    const engRef = doc(db, "engagements", engagementId);

    const unsubEng = onSnapshot(
      engRef,
      (snap) => {
        if (!snap.exists()) {
          setEngagement(null);
          setLoading(false);
          return;
        }

        const data = { id: snap.id, ...snap.data() } as Engagement;
        setEngagement(data);
        setSelectedAssigneeIds(data.assignedTeamMemberIds || []);

        // Fetch Client
        if (data.clientId) {
          onSnapshot(doc(db, "clients", data.clientId), (cSnap) => {
            if (cSnap.exists()) setClient({ id: cSnap.id, ...cSnap.data() } as Client);
          });
        }

        // Fetch Service
        if (data.serviceId) {
          onSnapshot(doc(db, "services", data.serviceId), (sSnap) => {
            if (sSnap.exists()) {
              setService({ id: sSnap.id, ...sSnap.data() } as Service);
            } else {
              const cfg = SERVICES_CONFIG[data.serviceId];
              setService({
                id: data.serviceId,
                name: cfg?.name || data.serviceId,
                consentTemplate: { body: "Standard engagement template", version: "1.0" },
                retentionPolicy: { basis: cfg?.basis || "contract_tenure", years: cfg?.years, statute: cfg?.statute || "Statute" }
              });
            }
          });
        }

        setLoading(false);
      },
      (err) => {
        console.error("Engagement detail snapshot error:", err);
        setLoading(false);
      }
    );

    return () => unsubEng();
  }, [engagementId]);

  // 2. Real-Time Users Listener (for resolving staff names & re-assigning)
  useEffect(() => {
    const unsubUsers = onSnapshot(
      collection(db, "users"),
      (snap) => {
        const staffList: UserProfile[] = [];
        const usersMap: Record<string, UserProfile> = {};

        snap.forEach((dSnap) => {
          const u = { uid: dSnap.id, ...dSnap.data() } as UserProfile;
          usersMap[u.uid] = u;
          if (u.role === "team_member") {
            staffList.push(u);
          }
        });

        setTeamMembers(staffList);
        setAllUsersMap(usersMap);
      },
      (err) => {
        console.error("Users snapshot error:", err);
      }
    );

    return () => unsubUsers();
  }, []);

  // Helper: check if current user is authorized to access this engagement
  const isAssignedToThisEngagement =
    userProfile.role === "full_admin" ||
    (userProfile.role === "team_member" && engagement?.assignedTeamMemberIds?.includes(userProfile.uid)) ||
    (userProfile.role === "client" && engagement?.clientId === userProfile.linkedClientId);

  // 2. Real-Time Documents Subcollection Listener with Role-Based Query Filtering
  useEffect(() => {
    if (!engagementId || !engagement) return;
    if (userProfile.role === "team_member" && (!engagement.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid))) {
      setDocuments([]);
      return;
    }

    const docsRef = collection(db, "engagements", engagementId, "documents");
    const isClientRole = userProfile?.role === "client";

    // Strict Query Enforcement:
    // Clients ONLY fetch documents where uploadedByRole == "client"
    // Firm staff (team_member / full_admin) fetch all documents
    const q = isClientRole
      ? query(docsRef, where("uploadedByRole", "==", "client"))
      : query(docsRef, orderBy("uploadedAt", "desc"));

    const unsubDocs = onSnapshot(
      q,
      (snap) => {
        const list: EngagementDocument[] = [];
        snap.forEach((docSnap) => {
          list.push({ id: docSnap.id, ...docSnap.data() } as EngagementDocument);
        });

        // Ensure chronological descending order
        list.sort((a, b) => {
          const tA = a.uploadedAt?.seconds
            ? a.uploadedAt.seconds * 1000
            : a.uploadedAt
            ? new Date(a.uploadedAt).getTime()
            : 0;
          const tB = b.uploadedAt?.seconds
            ? b.uploadedAt.seconds * 1000
            : b.uploadedAt
            ? new Date(b.uploadedAt).getTime()
            : 0;
          return tB - tA;
        });

        setDocuments(list);
      },
      (err) => {
        console.error("Documents snapshot error:", err);
      }
    );

    return () => unsubDocs();
  }, [engagementId, engagement?.assignedTeamMemberIds, userProfile?.role, userProfile?.uid]);

  // 3. Real-Time Client Comments Subcollection Listener (Append-Only)
  useEffect(() => {
    if (!engagementId || !engagement) return;
    if (userProfile.role === "team_member" && (!engagement.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid))) {
      setComments([]);
      return;
    }

    const commentsRef = collection(db, "engagements", engagementId, "clientComments");
    const q = query(commentsRef, orderBy("timestamp", "asc"));

    const unsubComments = onSnapshot(
      q,
      (snap) => {
        const list: ClientComment[] = [];
        snap.forEach((cSnap) => {
          list.push({ id: cSnap.id, ...cSnap.data() } as ClientComment);
        });
        setComments(list);
      },
      (err) => {
        console.error("Client comments snapshot error:", err);
      }
    );

    return () => unsubComments();
  }, [engagementId, engagement?.assignedTeamMemberIds, userProfile?.role, userProfile?.uid]);

  // 4. Real-Time Pending Items Subcollection Listener
  useEffect(() => {
    if (!engagementId || !engagement) return;
    if (userProfile.role === "team_member" && (!engagement.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid))) {
      setPendingItems([]);
      return;
    }

    const itemsRef = collection(db, "engagements", engagementId, "pendingItems");
    const q = query(itemsRef, orderBy("timestamp", "desc"));

    const unsubPendingItems = onSnapshot(
      q,
      (snap) => {
        const list: PendingItem[] = [];
        snap.forEach((docSnap) => {
          list.push({ id: docSnap.id, ...docSnap.data() } as PendingItem);
        });
        setPendingItems(list);
      },
      (err) => {
        console.error("Pending items snapshot error:", err);
      }
    );

    return () => unsubPendingItems();
  }, [engagementId, engagement?.assignedTeamMemberIds, userProfile?.role, userProfile?.uid]);

  // 5. Real-Time Review Notes Subcollection Listener (Strictly internal to full_admin & assigned team_member)
  // CRITICAL SECURITY RULE: Client role and unassigned team members MUST NOT FETCH THIS DATA!
  useEffect(() => {
    if (!engagementId || !engagement || userProfile.role === "client") {
      setReviewNotes([]);
      return;
    }

    if (userProfile.role === "team_member" && (!engagement.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid))) {
      setReviewNotes([]);
      return;
    }

    const notesRef = collection(db, "engagements", engagementId, "reviewNotes");
    const q = query(notesRef, orderBy("timestamp", "asc"));

    const unsubReviewNotes = onSnapshot(
      q,
      (snap) => {
        const list: ReviewNote[] = [];
        snap.forEach((docSnap) => {
          list.push({ id: docSnap.id, ...docSnap.data() } as ReviewNote);
        });
        setReviewNotes(list);
      },
      (err) => {
        console.error("Review notes snapshot error:", err);
      }
    );

    return () => unsubReviewNotes();
  }, [engagementId, engagement?.assignedTeamMemberIds, userProfile.role, userProfile.uid]);

  // Action: Send Consent Email (Admin)
  const handleSendConsentEmail = async () => {
    if (!engagement || !client) return;
    setSendingEmail(true);
    setActionError(null);
    setEmailProof(null);

    try {
      const resp = await fetch("/api/send-consent-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engagementId: engagement.id,
          clientEmail: client.email,
          clientName: client.name,
          serviceName: service?.name || engagement.serviceId,
          erasureDueDate: engagement.erasureDueDate
        })
      });

      const data = await resp.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to send consent email");
      }

      setEmailProof(data.emailResult || data.proof);
    } catch (err: any) {
      console.error("Send email error:", err);
      setActionError(err.message || "Failed to send consent email.");
    } finally {
      setSendingEmail(false);
    }
  };

  // Action: Move Status (WIP -> BEING_REVIEWED -> APPROVED or Send Back)
  const handleUpdateStatus = async (newStatus: "WIP" | "BEING_REVIEWED" | "APPROVED", notes?: string) => {
    if (!engagement) return;
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);
      const updatePayload: any = {
        status: newStatus,
        updatedAt: serverTimestamp()
      };

      if (notes && notes.trim()) {
        // Append as a new entry into the unified reviewNotes subcollection thread
        const notesRef = collection(db, "engagements", engagement.id, "reviewNotes");
        await addDoc(notesRef, {
          authorId: userProfile.uid,
          authorName: userProfile.displayName || "Senior Partner (Admin)",
          authorRole: "full_admin",
          entryType: "review_comment",
          text: notes.trim(),
          timestamp: serverTimestamp()
        });
      }

      await updateDoc(engRef, updatePayload);
      setIsSendBackOpen(false);
      setSendNote("");
    } catch (err: any) {
      setActionError(`Status update failed: ${err.message}`);
    }
  };

  // Action: Save Team Assignment (Admin)
  const handleSaveAssignment = async () => {
    if (!engagement) return;
    setSavingAssignment(true);
    setActionError(null);

    try {
      const resp = await fetch(`/api/engagements/${engagement.id}/assign-team`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assignedTeamMemberIds: selectedAssigneeIds,
          actorUid: userProfile.uid,
          actorEmail: userProfile.email,
        }),
      });

      const resData = await resp.json();
      if (!resData.success) {
        throw new Error(resData.error || "Failed to update team assignment");
      }

      setIsAssignModalOpen(false);
    } catch (err: any) {
      console.error("Failed to save team assignment:", err);
      setActionError(`Failed to save team assignment: ${err.message}`);
    } finally {
      setSavingAssignment(false);
    }
  };

  // Action: Client Give Consent
  const handleGiveConsent = async () => {
    if (!engagement) return;
    setUpdatingConsent(true);
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);
      await updateDoc(engRef, {
        consentStatus: "GIVEN",
        updatedAt: serverTimestamp()
      });

      // Append to append-only consentLog
      await addDoc(collection(db, "consentLog"), {
        engagementId: engagement.id,
        clientId: engagement.clientId,
        serviceId: engagement.serviceId,
        serviceName: service?.name || engagement.serviceId,
        action: "GIVEN",
        timestamp: serverTimestamp(),
        actorUid: userProfile.uid,
        actorEmail: userProfile.email,
        clientEmail: client?.email || userProfile.email,
        notes: `Client gave explicit DPDP consent for ${service?.name || engagement.serviceId}. Sub-folder unlocked.`
      });
    } catch (err: any) {
      console.error("Failed to give consent:", err);
      setActionError(`Failed to grant consent: ${err.message}`);
    } finally {
      setUpdatingConsent(false);
    }
  };

  // Action: Client Decline Consent
  const handleDeclineConsent = async () => {
    if (!engagement) return;
    setUpdatingConsent(true);
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);
      await updateDoc(engRef, {
        consentStatus: "DECLINED",
        updatedAt: serverTimestamp()
      });

      // Append to append-only consentLog
      await addDoc(collection(db, "consentLog"), {
        engagementId: engagement.id,
        clientId: engagement.clientId,
        serviceId: engagement.serviceId,
        serviceName: service?.name || engagement.serviceId,
        action: "DECLINED",
        timestamp: serverTimestamp(),
        actorUid: userProfile.uid,
        actorEmail: userProfile.email,
        clientEmail: client?.email || userProfile.email,
        notes: `Client actively declined DPDP consent for ${service?.name || engagement.serviceId}.`
      });
    } catch (err: any) {
      console.error("Failed to decline consent:", err);
      setActionError(`Failed to decline consent: ${err.message}`);
    } finally {
      setUpdatingConsent(false);
    }
  };

  // Action: Client Withdraw Consent
  const handleWithdrawConsent = async () => {
    if (!engagement) return;
    setActionError(null);

    try {
      const engRef = doc(db, "engagements", engagement.id);
      await updateDoc(engRef, {
        consentStatus: "WITHDRAWN",
        updatedAt: serverTimestamp()
      });

      // Append to consentLog
      await addDoc(collection(db, "consentLog"), {
        engagementId: engagement.id,
        clientId: engagement.clientId,
        serviceId: engagement.serviceId,
        serviceName: service?.name || engagement.serviceId,
        action: "WITHDRAWN",
        timestamp: serverTimestamp(),
        actorUid: userProfile.uid,
        actorEmail: userProfile.email,
        clientEmail: client?.email || userProfile.email || "",
        notes: "Consent withdrawn by client from folder view."
      });
    } catch (err: any) {
      setActionError(`Withdrawal failed: ${err.message}`);
    }
  };

  // File selection handlers
  const handleSelectFile = (file: File) => {
    setSelectedFile(file);
    setActionError(null);
    setUploadSuccessMsg(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleSelectFile(e.target.files[0]);
    }
  };

  const handleClearSelectedFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Action: Upload Document
  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setActionError("Please choose a file from your device before uploading.");
      return;
    }
    if (!engagement) return;

    if (userProfile.role === "team_member" && (!engagement.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid))) {
      setActionError("Access denied: You are not assigned to this engagement. Only assigned team members or administrators can upload documents.");
      return;
    }

    setUploadingDoc(true);
    setActionError(null);
    setUploadSuccessMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("uploadedByUid", userProfile.uid);
      formData.append("uploadedByName", userProfile.displayName || userProfile.email);
      formData.append("uploadedByRole", userProfile.role);
      formData.append("actorEmail", userProfile.email);
      if (engagement.clientId) {
        formData.append("clientId", engagement.clientId);
      }

      const resp = await fetch(`/api/engagements/${engagement.id}/upload-document`, {
        method: "POST",
        body: formData,
      });

      // Robustly read response body as text first to avoid stream consumption issues or CORS header masking
      const rawText = await resp.text();
      let resData: any = null;
      try {
        resData = JSON.parse(rawText);
      } catch {
        resData = null;
      }

      // Check for HTTP errors (4xx / 5xx)
      if (!resp.ok) {
        const errorMsg =
          resData?.error ||
          `Upload failed with HTTP ${resp.status}${rawText ? `: ${rawText.slice(0, 120)}` : ""}`;
        throw new Error(errorMsg);
      }

      // Verify payload contract for successful uploads
      if (!resData || resData.success !== true || !resData.document) {
        throw new Error(
          resData?.error || "Upload was received by the server but returned an unexpected response structure."
        );
      }

      setUploadSuccessMsg(`Successfully uploaded "${selectedFile.name}" to this engagement folder.`);
      setActionError(null);
      handleClearSelectedFile();
      setTimeout(() => setUploadSuccessMsg(null), 6000);
    } catch (err: any) {
      console.error("Document upload error:", err);
      setUploadSuccessMsg(null);
      setActionError(`Document upload failed: ${err.message}`);
    } finally {
      setUploadingDoc(false);
    }
  };

  // Robust File Download Handler with Blob Extraction
  const handleDownloadDocument = async (docItem: EngagementDocument) => {
    const filename = docItem.fileName || docItem.name || "document.pdf";
    const downloadUrl = `${docItem.url}${docItem.url.includes("?") ? "&" : "?"}role=${userProfile.role}&uid=${userProfile.uid}`;

    try {
      setDownloadingDocId(docItem.id);
      
      const response = await fetch(downloadUrl);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Download failed with HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      
      const downloadAnchor = document.createElement("a");
      downloadAnchor.href = blobUrl;
      downloadAnchor.download = filename;
      downloadAnchor.target = "_self";
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();

      setTimeout(() => {
        if (downloadAnchor.parentNode) {
          document.body.removeChild(downloadAnchor);
        }
        window.URL.revokeObjectURL(blobUrl);
      }, 500);
    } catch (err: any) {
      console.error("Download execution error:", err);
      // Fallback: direct window location trigger
      try {
        window.location.href = downloadUrl;
      } catch (fallbackErr) {
        alert(`Failed to download "${filename}": ${err.message}`);
      }
    } finally {
      setDownloadingDocId(null);
    }
  };

  // Helper: Format Timestamp for Comments
  const formatCommentTimestamp = (ts: any): string => {
    if (!ts) return "Just now";
    try {
      if (ts.toDate && typeof ts.toDate === "function") {
        return ts.toDate().toLocaleString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit"
        });
      }
      if (ts.seconds) {
        return new Date(ts.seconds * 1000).toLocaleString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit"
        });
      }
      const d = new Date(ts);
      if (!isNaN(d.getTime())) {
        return d.toLocaleString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit"
        });
      }
      return "Just now";
    } catch {
      return "Just now";
    }
  };

  // Action: Post Client Comment (One-Way Client-Only Channel to respond to Pending Items)
  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || !engagement) return;
    if (userProfile.role !== "client") {
      setCommentError("Only the client account can post entries in this responses thread.");
      return;
    }

    setPostingComment(true);
    setCommentError(null);
    setCommentSuccessMsg(null);

    try {
      const commentsRef = collection(db, "engagements", engagement.id, "clientComments");
      await addDoc(commentsRef, {
        authorId: userProfile.uid,
        authorName: userProfile.displayName || client?.name || userProfile.email || "Client",
        authorRole: "client",
        text: commentText.trim(),
        timestamp: serverTimestamp()
      });

      setCommentText("");
      setCommentSuccessMsg("Response posted to engagement record.");
      setTimeout(() => setCommentSuccessMsg(null), 4000);
    } catch (err: any) {
      console.error("Error posting client comment:", err);
      setCommentError(err.message || "Failed to post comment");
    } finally {
      setPostingComment(false);
    }
  };

  // Action: Post Internal Review Note (Firm staff & admin only)
  const handlePostReviewNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewNoteText.trim() || !engagement) return;
    if (userProfile.role === "client") return;

    setPostingReviewNote(true);
    setReviewNoteError(null);
    setReviewNoteSuccessMsg(null);

    try {
      const notesRef = collection(db, "engagements", engagement.id, "reviewNotes");
      await addDoc(notesRef, {
        authorId: userProfile.uid,
        authorName: userProfile.displayName || (userProfile.role === "full_admin" ? "Senior Partner (Admin)" : "Audit Staff"),
        authorRole: userProfile.role,
        entryType: "review_comment",
        text: reviewNoteText.trim(),
        timestamp: serverTimestamp()
      });

      setReviewNoteText("");
      setReviewNoteSuccessMsg("Internal review note added to engagement audit trail.");
      setTimeout(() => setReviewNoteSuccessMsg(null), 4000);
    } catch (err: any) {
      console.error("Error posting review note:", err);
      setReviewNoteError(err.message || "Failed to add review note");
    } finally {
      setPostingReviewNote(false);
    }
  };

  // Action: Add Pending Item (team_member / full_admin)
  const handleCreatePendingItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingItemText.trim() || !engagement) return;

    setPostingPendingItem(true);
    setPendingItemError(null);
    setPendingItemSuccessMsg(null);

    try {
      const resp = await fetch(`/api/engagements/${engagement.id}/pending-items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: pendingItemText.trim(),
          authorId: userProfile.uid,
          authorName: userProfile.displayName || userProfile.email || "Staff Member",
          authorRole: userProfile.role,
        }),
      });

      const data = await resp.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to create pending item");
      }

      setPendingItemText("");
      setPendingItemSuccessMsg(
        data.emailResult?.sent
          ? "Pending item added and client notified via email."
          : "Pending item added to engagement record."
      );
      setTimeout(() => setPendingItemSuccessMsg(null), 5000);
    } catch (err: any) {
      console.error("Error creating pending item:", err);
      setPendingItemError(err.message || "Failed to create pending item");
    } finally {
      setPostingPendingItem(false);
    }
  };

  // Action: Toggle Resolved / Open Status on a Pending Item (team_member / full_admin)
  const handleToggleResolvePendingItem = async (item: PendingItem) => {
    if (!engagement) return;
    const newStatus = item.status === "resolved" ? "open" : "resolved";

    setResolvingItemId(item.id);
    setPendingItemError(null);

    try {
      const resp = await fetch(`/api/engagements/${engagement.id}/pending-items/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: newStatus,
          actorId: userProfile.uid,
          actorName: userProfile.displayName || userProfile.email || "Staff Member",
          actorRole: userProfile.role,
        }),
      });

      const data = await resp.json();
      if (!data.success) {
        throw new Error(data.error || "Failed to update item status");
      }
    } catch (err: any) {
      console.error("Error updating pending item status:", err);
      setPendingItemError(err.message || "Failed to update item status");
    } finally {
      setResolvingItemId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-slate-400">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading engagement folder details...</span>
        </div>
      </div>
    );
  }

  if (!engagement) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl text-white space-y-4">
        <p className="text-rose-400 font-semibold">Engagement folder not found.</p>
        <button onClick={onBack} className="px-4 py-2 bg-slate-800 text-xs rounded-lg">
          ← Back to Service Folders
        </button>
      </div>
    );
  }

  // Access Guard: Team members can ONLY view engagements they are assigned to
  if (
    userProfile.role === "team_member" &&
    (!engagement.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid))
  ) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-colors border border-slate-700"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Service Folders
          </button>
        </div>

        <div className="p-8 bg-slate-900 border border-slate-800 rounded-2xl text-white space-y-4 text-center max-w-xl mx-auto shadow-2xl">
          <div className="w-12 h-12 rounded-full bg-rose-950/80 border border-rose-800/80 flex items-center justify-center mx-auto text-rose-400">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white">Access Restricted to Assigned Staff</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            You are not assigned to this client engagement folder. In accordance with firm access controls, working papers, review notes, pending items, and client records are restricted strictly to assigned team members and Senior Partners.
          </p>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-colors cursor-pointer"
          >
            ← Return to Service Folders
          </button>
        </div>
      </div>
    );
  }

  const isClientRole = userProfile.role === "client";
  const isConsentGiven = engagement.consentStatus === "GIVEN";
  const isLockedForClient = isClientRole && !isConsentGiven;

  return (
    <div className="space-y-6">
      
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-colors border border-slate-700"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Service Folders
        </button>

        <div className="text-xs text-slate-400 flex items-center gap-2 font-mono">
          <span>{service?.name || engagement.serviceId}</span>
          <span>/</span>
          <span className="text-indigo-400 font-bold">{client?.name || "Client"}</span>
        </div>
      </div>

      {/* Action error banner */}
      {actionError && (
        <div className="p-3.5 bg-rose-950/80 border border-rose-800 text-rose-200 text-xs rounded-xl flex items-start gap-2">
          <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Main Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
              Top-Level Service Folder: {service?.name}
            </div>
            <h2 className="text-2xl font-extrabold text-white flex items-center gap-2">
              <FolderOpen className="w-6 h-6 text-indigo-500" />
              {client?.name || "Client Entity"}
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Client Contact: {client?.email} | Entity Type: {client?.entityType === "company" ? "Company (Companies Act s.138)" : "Non-Company"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Status Badges */}
            <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
              engagement.status === "APPROVED"
                ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                : engagement.status === "BEING_REVIEWED"
                ? "bg-amber-950 text-amber-300 border-amber-800"
                : "bg-slate-800 text-slate-300 border-slate-700"
            }`}>
              Folder Status: {engagement.status}
            </span>

            <span className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 ${
              engagement.consentStatus === "GIVEN"
                ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                : engagement.consentStatus === "SENT"
                ? "bg-sky-950 text-sky-300 border-sky-800"
                : engagement.consentStatus === "SEND_FAILED"
                ? "bg-rose-950 text-rose-300 border-rose-800"
                : engagement.consentStatus === "WITHDRAWN"
                ? "bg-orange-950 text-orange-300 border-orange-800"
                : "bg-amber-950 text-amber-300 border-amber-800"
            }`}>
              {engagement.consentStatus === "GIVEN" && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
              {engagement.consentStatus === "SENT" && <Send className="w-3.5 h-3.5 text-sky-400" />}
              {engagement.consentStatus === "SEND_FAILED" && <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />}
              Consent: {
                engagement.consentStatus === "SENT"
                  ? "Notice Emailed"
                  : engagement.consentStatus === "SEND_FAILED"
                  ? "Email Send Failed"
                  : engagement.consentStatus === "GIVEN"
                  ? "Consent Given"
                  : engagement.consentStatus === "WITHDRAWN"
                  ? "Consent Withdrawn"
                  : "Consent Pending"
              }
            </span>
          </div>
        </div>

        {/* Failed Email Delivery Alert with Retry */}
        {engagement.consentStatus === "SEND_FAILED" && (
          <div className="p-4 bg-rose-950/80 border border-rose-800 rounded-xl text-xs text-rose-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block text-rose-300">Email Delivery Failed:</strong>
                <span className="text-rose-200">{engagement.emailDelivery?.error || "Unable to dispatch consent notice email via SMTP transporter."}</span>
              </div>
            </div>
            {userProfile.role === "full_admin" && (
              <button
                type="button"
                disabled={sendingEmail}
                onClick={handleSendConsentEmail}
                className="px-3.5 py-1.5 bg-rose-700 hover:bg-rose-600 text-white font-semibold text-xs rounded-lg shadow shrink-0 flex items-center gap-1.5 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                {sendingEmail ? "Retrying..." : "Retry Email Dispatch"}
              </button>
            )}
          </div>
        )}

        {/* Confirmed Delivery Banner */}
        {engagement.consentStatus === "SENT" && engagement.emailDelivery && (
          <div className="p-3 bg-sky-950/60 border border-sky-800/80 rounded-xl text-xs text-sky-200 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Send className="w-3.5 h-3.5 text-sky-400" />
              <span>
                <strong>Notice Dispatched via Real SMTP:</strong> {engagement.emailDelivery.method || "smtp.gmail.com"} | 
                Message ID: <span className="font-mono text-sky-300">{engagement.emailDelivery.messageId || "N/A"}</span>
              </span>
            </div>
            {engagement.emailDelivery.timestamp && (
              <span className="text-slate-400 text-[11px]">
                {new Date(engagement.emailDelivery.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>
        )}

        {/* Governance & Erasure Due Date Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs bg-slate-950/80 p-4 rounded-xl border border-slate-800">
          <div>
            <span className="text-slate-400 block mb-0.5">Statutory Retention Basis:</span>
            <span className="text-white font-mono font-semibold">
              {service?.retentionPolicy?.basis === "from_date" ? "Fixed Statutory Period (from_date)" : "Contract Tenure (contract_tenure)"}
            </span>
          </div>

          <div>
            <span className="text-slate-400 block mb-0.5">Statutory Standard:</span>
            <span className="text-slate-200 font-medium">
              {service?.retentionPolicy?.statute || "Statutory Law"}
            </span>
          </div>

          <div>
            <span className="text-slate-400 block mb-0.5">Assigned Team Staff:</span>
            <div className="text-white font-medium flex flex-wrap gap-1 mt-0.5">
              {engagement.assignedTeamMemberIds && engagement.assignedTeamMemberIds.length > 0 ? (
                engagement.assignedTeamMemberIds.map((uid) => (
                  <span key={uid} className="inline-flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded text-[11px] border border-slate-700 text-slate-200">
                    <Users className="w-3 h-3 text-indigo-400" />
                    {allUsersMap[uid]?.displayName || allUsersMap[uid]?.email || uid.slice(0, 8)}
                  </span>
                ))
              ) : (
                <span className="text-slate-500 italic">No staff assigned</span>
              )}
            </div>
          </div>

          <div className="bg-indigo-950/60 p-2.5 rounded-lg border border-indigo-800/80">
            <span className="text-indigo-300 block font-bold text-[11px] uppercase tracking-wide">
              Calculated Erasure Due Date
            </span>
            <span className="text-white font-mono font-bold text-base">
              {engagement.erasureDueDate}
            </span>
          </div>
        </div>

        {/* WORKFLOW CONTROLS BY ROLE */}
        <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800">
          
          {/* FULL ADMIN CONTROLS */}
          {userProfile.role === "full_admin" && (
            <div className="w-full flex flex-wrap items-center justify-between gap-3 bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80">
              <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-purple-400" />
                Admin Governance Actions:
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Manage Team Assignment Button */}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedAssigneeIds(engagement.assignedTeamMemberIds || []);
                    setIsAssignModalOpen(true);
                  }}
                  className="px-3.5 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-1.5"
                >
                  <Users className="w-3.5 h-3.5 text-indigo-300" />
                  Assign Team Members
                </button>

                {/* Send Consent Email Button */}
                <button
                  type="button"
                  disabled={sendingEmail}
                  onClick={handleSendConsentEmail}
                  className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  {sendingEmail ? "Dispatching Email..." : "Send Consent Request Email"}
                </button>

                {/* Approve Button */}
                {engagement.status !== "APPROVED" && (
                  <button
                    type="button"
                    onClick={() => handleUpdateStatus("APPROVED")}
                    className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-1.5"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Approve Folder
                  </button>
                )}

                {/* Send Back Button */}
                {engagement.status !== "WIP" && (
                  <button
                    type="button"
                    onClick={() => setIsSendBackOpen(!isSendBackOpen)}
                    className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Send Back
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TEAM MEMBER CONTROLS */}
          {userProfile.role === "team_member" && (
            <div className="w-full flex items-center justify-between bg-slate-800/60 p-3 rounded-xl border border-slate-700/80">
              <span className="text-xs text-slate-300 font-medium">Team Member Actions:</span>
              {engagement.status === "WIP" ? (
                <button
                  type="button"
                  onClick={() => handleUpdateStatus("BEING_REVIEWED")}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-2"
                >
                  <Clock className="w-3.5 h-3.5" />
                  Submit for Review
                </button>
              ) : (
                <span className="text-xs text-slate-400 font-mono">
                  Folder is currently: {engagement.status}
                </span>
              )}
            </div>
          )}

          {/* CLIENT CONTROLS */}
          {userProfile.role === "client" && isConsentGiven && (
            <div className="w-full flex items-center justify-between bg-emerald-950/40 p-3 rounded-xl border border-emerald-800/60">
              <span className="text-xs text-emerald-200 font-semibold flex items-center gap-2">
                <Unlock className="w-4 h-4 text-emerald-400" />
                Folder Unlocked. You have granted active consent.
              </span>

              <button
                type="button"
                onClick={handleWithdrawConsent}
                className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-1.5"
              >
                <Lock className="w-3.5 h-3.5" />
                Withdraw Consent
              </button>
            </div>
          )}

        </div>

        {/* Send Back Modal / Input Box */}
        {isSendBackOpen && (
          <div className="p-4 bg-amber-950/80 border border-amber-800 rounded-xl space-y-3">
            <label className="block text-xs font-semibold text-amber-200">
              Reason / Review Notes for Sending Back to WIP (Required):
            </label>
            <textarea
              required
              rows={2}
              value={sendNote}
              onChange={(e) => setSendNote(e.target.value)}
              placeholder="Specify required corrections or missing documents..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsSendBackOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!sendNote.trim()}
                onClick={() => handleUpdateStatus("WIP", sendNote.trim())}
                className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs rounded-lg shadow disabled:opacity-50"
              >
                Confirm Send Back to WIP
              </button>
            </div>
          </div>
        )}

        {/* Real SMTP Proof Banner */}
        {emailProof && (
          <div className="p-4 bg-blue-950/80 border border-blue-800 rounded-xl text-xs text-blue-200 space-y-2">
            <div className="font-bold text-blue-300 flex items-center gap-2">
              <Send className="w-4 h-4 text-blue-400" />
              Consent Request Dispatch Proof
            </div>
            <pre className="bg-slate-950 p-3 rounded-lg text-[11px] font-mono text-blue-400 overflow-x-auto">
              {JSON.stringify(emailProof, null, 2)}
            </pre>
          </div>
        )}

      </div>

      {/* CLIENT FOLDER LOCK ENFORCEMENT & DPDP CONSENT MECHANISM */}
      {isLockedForClient ? (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                <Lock className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-white">
                  DPDP Consent Required — Folder Locked
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Statutory authorization required for <strong>{service?.name || engagement.serviceId}</strong>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                engagement.consentStatus === "DECLINED"
                  ? "bg-rose-950/80 text-rose-300 border-rose-800"
                  : engagement.consentStatus === "WITHDRAWN"
                  ? "bg-amber-950/80 text-amber-300 border-amber-800"
                  : "bg-blue-950/80 text-blue-300 border-blue-800"
              }`}>
                Current Status: {engagement.consentStatus}
              </span>
            </div>
          </div>

          {/* Status Note if Declined or Withdrawn */}
          {engagement.consentStatus === "DECLINED" && (
            <div className="p-4 bg-rose-950/60 border border-rose-800/80 rounded-2xl text-xs text-rose-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block text-rose-300 font-semibold mb-0.5">Consent Declined</strong>
                You previously declined consent for this engagement. Access to upload or download files remains locked. You can review the notice below and click <strong>"I Consent"</strong> at any time to grant consent and unlock your folder.
              </div>
            </div>
          )}

          {engagement.consentStatus === "WITHDRAWN" && (
            <div className="p-4 bg-amber-950/60 border border-amber-800/80 rounded-2xl text-xs text-amber-200 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block text-amber-300 font-semibold mb-0.5">Consent Withdrawn</strong>
                You previously withdrew consent for this engagement. Document exchange is currently locked. Click <strong>"I Consent"</strong> below to grant consent and unlock the folder.
              </div>
            </div>
          )}

          {/* Statutory Retention & Erasure Due Date Display */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                Statutory Retention & Data Governance
              </span>
              <span className="text-xs bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded font-mono border border-slate-700">
                Basis: {service?.retentionPolicy?.basis === "from_date" ? "Statutory Period (from_date)" : "Contract Tenure (contract_tenure)"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Statute / Legal Retention Rule:</span>
                <span className="text-slate-200 font-medium">
                  {service?.retentionPolicy?.statute || "Standard statutory terms"}
                </span>
              </div>

              <div>
                <span className="text-slate-400 block mb-0.5">Engagement Contract Tenure:</span>
                <span className="text-slate-200 font-medium font-mono">
                  {engagement.contractStartDate} to {engagement.contractEndDate}
                </span>
              </div>
            </div>

            <div className="p-3.5 bg-indigo-950/50 border border-indigo-800/80 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wide">
                  Calculated Explicit Erasure Due Date
                </div>
                <div className="text-lg font-bold text-white font-mono mt-0.5">
                  {engagement.erasureDueDate}
                </div>
              </div>
              <div className="text-left sm:text-right text-[11px] text-slate-400 max-w-xs">
                Data scheduled for automatic erasure per statutory retention period + 60 days buffer.
              </div>
            </div>
          </div>

          {/* Full DPDP Notice Body */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-indigo-400" />
              DPDP Statutory Notice & Processing Purpose
            </label>
            <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-line font-sans border-l-4 border-l-indigo-500 shadow-inner">
              {service?.consentTemplate?.body || "Loading DPDP statutory notice text..."}
            </div>
          </div>

          {/* Error Message Display if Consent Action Fails */}
          {actionError && (
            <div className="p-4 bg-rose-950/90 border border-rose-700 rounded-2xl text-xs text-rose-200 flex items-start gap-3 shadow-lg animate-in fade-in">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block text-rose-300 font-bold mb-0.5">Action Error</strong>
                <span>{actionError}</span>
              </div>
            </div>
          )}

          {/* Action Buttons: I Consent and Decline */}
          <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-slate-400 text-center sm:text-left">
              By clicking <strong>"I Consent"</strong>, you grant explicit authorization to ABC & Associates to collect and process your engagement documents pursuant to the notice above.
            </p>

            <div className="flex items-center gap-3 w-full sm:w-auto shrink-0">
              <button
                type="button"
                disabled={updatingConsent}
                onClick={handleDeclineConsent}
                className="flex-1 sm:flex-none px-5 py-3 bg-slate-800 hover:bg-rose-950/80 text-rose-300 hover:text-rose-200 border border-slate-700 hover:border-rose-700 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <XCircle className="w-4 h-4 text-rose-400" />
                {updatingConsent ? "Updating..." : "Decline"}
              </button>

              <button
                type="button"
                disabled={updatingConsent}
                onClick={handleGiveConsent}
                className="flex-1 sm:flex-none px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs sm:text-sm rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <ShieldCheck className="w-4 h-4" />
                {updatingConsent ? "Updating Firestore..." : "I Consent"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* UNLOCKED DOCUMENT & COMMENTS WORKSPACE */
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" />
                {isClientRole ? "Engagement Documents & Deliverables" : "Engagement Documents Subcollection"}
              </h3>
              <p className="text-xs text-slate-400">
                {isClientRole
                  ? `Documents uploaded by you for ${service?.name || "this engagement"} (shared with ABC & Associates firm staff)`
                  : `Managed documents and confidential internal working papers for ${client?.name || "Client"} under ${service?.name || "Service"}`}
              </p>
            </div>
          </div>

          {/* Success / Error Feedback Banners */}
          {uploadSuccessMsg && (
            <div className="p-3 bg-emerald-950/80 border border-emerald-700/80 rounded-xl text-xs text-emerald-300 flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{uploadSuccessMsg}</span>
            </div>
          )}

          {actionError && (
            <div className="p-3 bg-rose-950/80 border border-rose-700/80 rounded-xl text-xs text-rose-300 flex items-center gap-2 animate-in fade-in">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          {/* Real File Upload & Dropzone Area or Unassigned Warning */}
          {userProfile.role === "team_member" && (!engagement?.assignedTeamMemberIds || !engagement.assignedTeamMemberIds.includes(userProfile.uid)) ? (
            <div className="p-4 bg-slate-950 border border-amber-800/60 rounded-2xl text-amber-300 text-xs flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-amber-200">Upload Restricted (Unassigned Team Member)</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  You are not assigned to this engagement. Only assigned team members ({engagement?.assignedTeamMemberIds?.map(id => allUsersMap[id]?.displayName || allUsersMap[id]?.email || id).join(", ") || "None"}) and firm administrators can upload working papers and documents.
                </p>
              </div>
            </div>
          ) : (
            <form
              onSubmit={handleUploadDocument}
              className="p-5 bg-slate-950 border border-slate-800 rounded-2xl space-y-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                  <FileUp className="w-4 h-4 text-indigo-400" />
                  Upload New Engagement Document
                </span>
                <span className="text-[11px] text-slate-400">
                  Allowed formats: PDF, DOCX, XLSX, CSV, JPG, PNG (Max 50MB)
                </span>
              </div>

              {/* Hidden Real HTML File Input */}
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileChange}
                className="hidden"
                id="engagement-file-input"
              />

              {/* Dropzone / File Picker Container */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    handleSelectFile(e.dataTransfer.files[0]);
                  }
                }}
                className={`border-2 border-dashed rounded-xl p-5 text-center transition-all ${
                  isDragging
                    ? "border-indigo-500 bg-indigo-950/30"
                    : selectedFile
                    ? "border-indigo-600/60 bg-indigo-950/20"
                    : "border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/80"
                }`}
              >
                {selectedFile ? (
                  /* Selected File Preview Box */
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-3 bg-slate-900 border border-indigo-500/40 rounded-xl">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-2.5 bg-indigo-950 text-indigo-400 rounded-lg border border-indigo-800 shrink-0">
                        <Paperclip className="w-5 h-5" />
                      </div>
                      <div className="text-left min-w-0">
                        <p className="text-xs font-bold text-white truncate max-w-md">
                          {selectedFile.name}
                        </p>
                        <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                          <span>Size: {(selectedFile.size / 1024).toFixed(1)} KB</span>
                          <span>•</span>
                          <span className="font-mono">{selectedFile.type || "file"}</span>
                          <span>•</span>
                          <span className="text-emerald-400 font-semibold">Ready to upload</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition-colors"
                      >
                        Change File
                      </button>
                      <button
                        type="button"
                        onClick={handleClearSelectedFile}
                        className="p-1.5 bg-slate-800 hover:bg-rose-950 text-slate-400 hover:text-rose-400 rounded-lg border border-slate-700 hover:border-rose-800 transition-colors"
                        title="Remove file"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ) : (
                  /* No File Selected State */
                  <div className="flex flex-col items-center justify-center space-y-2 py-2">
                    <div className="p-3 bg-slate-800/80 text-indigo-400 rounded-full">
                      <FileUp className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-200">
                        Drag & drop your file here, or{" "}
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="text-indigo-400 hover:text-indigo-300 underline font-bold focus:outline-none"
                        >
                          choose a file
                        </button>{" "}
                        from your computer
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {isClientRole
                          ? "Uploads will be saved under the documents subcollection and shared with ABC & Associates firm staff"
                          : "Uploads by firm staff are saved as Internal Working Papers (confidential to staff, hidden from client)"}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Form Actions & Upload Button */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                <div className="text-[11px] text-slate-400">
                  {selectedFile ? (
                    <span className="text-indigo-300 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                      1 file selected ({isClientRole ? "Client Document" : "Internal Working Paper"}). Click below to upload.
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">
                      No file chosen. Please select a file from your device first.
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {!selectedFile && (
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 transition-colors flex items-center gap-1.5"
                    >
                      <Paperclip className="w-3.5 h-3.5 text-indigo-400" />
                      Choose File
                    </button>
                  )}

                  <button
                    type="submit"
                    disabled={uploadingDoc || !selectedFile}
                    className={`px-5 py-2 text-xs font-bold rounded-xl shadow transition-all flex items-center gap-2 ${
                      !selectedFile || uploadingDoc
                        ? "bg-slate-800 text-slate-500 cursor-not-allowed opacity-60 border border-slate-700"
                        : "bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer shadow-indigo-900/40"
                    }`}
                    title={!selectedFile ? "Please select a file first" : "Upload Document"}
                  >
                    <Upload className={`w-4 h-4 ${uploadingDoc ? "animate-bounce" : ""}`} />
                    {uploadingDoc ? "Uploading to Storage..." : isClientRole ? "Upload Client Document" : "Upload Working Paper"}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Documents Table / List */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                {isClientRole ? "Uploaded Client Documents" : "Uploaded Folder Files & Working Papers"} ({documents.length})
              </h4>
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
                <FileText className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                {isClientRole
                  ? "No documents uploaded to this engagement folder yet. Select a file above to add it."
                  : "No documents or working papers uploaded to this engagement folder yet."}
              </div>
            ) : (
              <div className="space-y-2.5">
                {documents.map((docItem) => {
                  const displayFileName = docItem.fileName || docItem.name || "Document";
                  const isUploadedByClient = docItem.uploadedByRole === "client";
                  const formattedSize = docItem.fileSize
                    ? docItem.fileSize > 1024 * 1024
                      ? `${(docItem.fileSize / (1024 * 1024)).toFixed(2)} MB`
                      : `${(docItem.fileSize / 1024).toFixed(1)} KB`
                    : "Unknown size";

                  const isSelfUpload =
                    userProfile.role === "team_member" &&
                    (docItem.uploadedByUid === userProfile.uid || docItem.uploadedBy === userProfile.email);

                  return (
                    <div
                      key={docItem.id}
                      className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`p-2.5 rounded-lg shrink-0 border ${
                          isUploadedByClient
                            ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/40"
                            : "bg-amber-950/40 text-amber-400 border-amber-800/40"
                        }`}>
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <button
                              type="button"
                              onClick={() => handleDownloadDocument(docItem)}
                              className="text-xs font-bold text-white hover:text-indigo-300 transition-colors truncate block text-left underline decoration-slate-600 underline-offset-2 cursor-pointer"
                              title={`Click to download ${displayFileName}`}
                            >
                              {displayFileName}
                            </button>
                            {isUploadedByClient ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 flex items-center gap-1">
                                <FileText className="w-2.5 h-2.5 text-emerald-400" />
                                Client Upload
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/80 flex items-center gap-1">
                                <Lock className="w-2.5 h-2.5 text-amber-400" />
                                Internal Working Paper (Staff Only)
                              </span>
                            )}
                            {isSelfUpload && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80 flex items-center gap-1">
                                <CheckCircle2 className="w-2.5 h-2.5 text-indigo-400" />
                                Your Upload
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-slate-400 mt-0.5 flex flex-wrap items-center gap-x-2.5 gap-y-1">
                            <span>
                              Uploaded by: <strong className="text-slate-300">{docItem.uploadedByName || docItem.uploadedBy || "User"}</strong> ({docItem.uploadedByRole})
                            </span>
                            <span>•</span>
                            <span>Size: {formattedSize}</span>
                            {docItem.storagePath && (
                              <>
                                <span>•</span>
                                <span className="font-mono text-[9px] text-slate-500 truncate max-w-xs" title={docItem.storagePath}>
                                  Path: {docItem.storagePath}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          id={`download-btn-${docItem.id}`}
                          disabled={downloadingDocId === docItem.id}
                          onClick={() => handleDownloadDocument(docItem)}
                          className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm text-center flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                          title={`Download ${displayFileName} to your computer`}
                        >
                          <Download className={`w-3.5 h-3.5 text-indigo-200 ${downloadingDocId === docItem.id ? "animate-bounce" : ""}`} />
                          {downloadingDocId === docItem.id ? "Downloading..." : "Download File"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* PENDING ITEMS / ACTION REQUIRED SECTION */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <ListTodo className="w-5 h-5 text-amber-400" />
                Pending Items / Action Required
              </h3>
              <p className="text-xs text-slate-400">
                {isClientRole
                  ? "Action items and deliverables requested by your engagement team at ABC & Associates."
                  : `Firm action notices and required deliverables for ${client?.name || "the client"}.`}
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0 flex-wrap">
              {pendingItems.filter((i) => i.status === "open").length > 0 ? (
                <span className="px-3 py-1 bg-amber-950/80 text-amber-300 border border-amber-700/80 rounded-full text-[11px] font-semibold flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  {pendingItems.filter((i) => i.status === "open").length} Action Required
                </span>
              ) : (
                <span className="px-3 py-1 bg-emerald-950/80 text-emerald-300 border border-emerald-700/80 rounded-full text-[11px] font-semibold flex items-center gap-1.5">
                  <CheckSquare className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  All Items Resolved
                </span>
              )}

              {pendingItems.filter((i) => i.status === "resolved").length > 0 && (
                <span className="px-3 py-1 bg-slate-800 text-slate-400 border border-slate-700 rounded-full text-[11px] font-medium">
                  {pendingItems.filter((i) => i.status === "resolved").length} Resolved
                </span>
              )}
            </div>
          </div>

          {/* Feedback Banners */}
          {pendingItemSuccessMsg && (
            <div className="p-3 bg-emerald-950/80 border border-emerald-700/80 rounded-xl text-xs text-emerald-300 flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{pendingItemSuccessMsg}</span>
            </div>
          )}

          {pendingItemError && (
            <div className="p-3 bg-rose-950/80 border border-rose-700/80 rounded-xl text-xs text-rose-300 flex items-center gap-2 animate-in fade-in">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{pendingItemError}</span>
            </div>
          )}

          {/* Pending Items List */}
          <div className="space-y-3">
            {pendingItems.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-1.5">
                <ListTodo className="w-8 h-8 text-slate-700 mx-auto" />
                <p className="font-semibold text-slate-400">No pending action items recorded.</p>
                <p className="text-[11px] text-slate-500">
                  {isClientRole
                    ? "There are currently no outstanding requirements or queries requested for this engagement."
                    : "Team members and administrators can add action requests (e.g., missing TDS certificates, reconciliations) at any point."}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingItems.map((item) => {
                  const isOpen = item.status === "open";
                  const isResolving = resolvingItemId === item.id;

                  return (
                    <div
                      key={item.id}
                      className={`p-4 rounded-xl border transition-all ${
                        isOpen
                          ? "bg-amber-950/15 border-amber-800/40 hover:border-amber-700/60"
                          : "bg-slate-950/60 border-slate-800/80 opacity-75 hover:opacity-100"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div className="space-y-2 flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`px-2.5 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase border flex items-center gap-1 ${
                                isOpen
                                  ? "bg-amber-950 text-amber-300 border-amber-700"
                                  : "bg-emerald-950 text-emerald-300 border-emerald-800"
                              }`}
                            >
                              {isOpen ? (
                                <>
                                  <AlertCircle className="w-3 h-3 text-amber-400" />
                                  Action Required
                                </>
                              ) : (
                                <>
                                  <CheckSquare className="w-3 h-3 text-emerald-400" />
                                  Resolved
                                </>
                              )}
                            </span>

                            <span className="text-[11px] text-slate-400">
                              Requested by <strong className="text-slate-300">{item.authorName}</strong>{" "}
                              <span className="text-slate-500">({item.authorRole === "full_admin" ? "Admin" : "Assigned Staff"})</span>
                            </span>

                            <span className="text-slate-600">•</span>

                            <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-500" />
                              {formatCommentTimestamp(item.timestamp)}
                            </span>
                          </div>

                          <div
                            className={`text-xs sm:text-sm font-medium leading-relaxed ${
                              isOpen ? "text-slate-100 font-semibold" : "text-slate-400 line-through decoration-slate-600"
                            }`}
                          >
                            {item.text}
                          </div>

                          {!isOpen && item.resolvedByName && (
                            <div className="text-[10px] text-emerald-400/90 flex items-center gap-1 pt-0.5">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                              <span>
                                Marked resolved by <strong>{item.resolvedByName}</strong>
                                {item.resolvedAt ? ` on ${formatCommentTimestamp(item.resolvedAt)}` : ""}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Staff Status Toggle Action (Only team_member & full_admin) */}
                        {!isClientRole && (
                          <div className="shrink-0 flex items-center pt-1 sm:pt-0">
                            {isOpen ? (
                              <button
                                type="button"
                                disabled={isResolving}
                                onClick={() => handleToggleResolvePendingItem(item)}
                                className="px-3.5 py-1.5 bg-emerald-700/80 hover:bg-emerald-600 text-white text-xs font-semibold rounded-lg shadow transition-all flex items-center gap-1.5 disabled:opacity-50"
                                title="Mark item as resolved"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                {isResolving ? "Updating..." : "Mark Resolved"}
                              </button>
                            ) : (
                              <button
                                type="button"
                                disabled={isResolving}
                                onClick={() => handleToggleResolvePendingItem(item)}
                                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium rounded-lg border border-slate-700 transition-all flex items-center gap-1.5 disabled:opacity-50"
                                title="Reopen action item"
                              >
                                <RotateCcw className="w-3 h-3" />
                                {isResolving ? "Updating..." : "Reopen Item"}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Form for Staff to Add Pending Items at ANY point during the engagement lifecycle */}
          {!isClientRole ? (
            <form
              onSubmit={handleCreatePendingItem}
              className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <label
                  htmlFor="new-pending-item-textarea"
                  className="text-xs font-bold text-amber-300 flex items-center gap-1.5"
                >
                  <ListTodo className="w-3.5 h-3.5 text-amber-400" />
                  Add Pending Item / Action Required
                </label>

                <span className="text-[11px] text-slate-400">
                  Visible to client • Sends generic email notice
                </span>
              </div>

              <textarea
                id="new-pending-item-textarea"
                required
                rows={2}
                value={pendingItemText}
                onChange={(e) => setPendingItemText(e.target.value)}
                placeholder="e.g. Please share reconciliation of receivables, TDS certificate for Q3 missing..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors resize-y"
              />

              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
                <div className="text-[11px] text-slate-500 flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span>
                    Available throughout the engagement lifecycle (WIP, Being Reviewed, or Approved).
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={postingPendingItem || !pendingItemText.trim()}
                  className={`px-5 py-2 text-xs font-bold rounded-xl shadow transition-all flex items-center gap-1.5 shrink-0 ${
                    !pendingItemText.trim() || postingPendingItem
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed opacity-60 border border-slate-700"
                      : "bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold cursor-pointer shadow-amber-900/40"
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  {postingPendingItem ? "Adding & Notifying..." : "Add Pending Item"}
                </button>
              </div>
            </form>
          ) : (
            <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs text-slate-400 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>
                One-way firm notices from ABC & Associates. Once you supply the requested materials, your engagement team will update and resolve the items above.
              </span>
            </div>
          )}
        </div>

        {/* CLIENT COMMENTS & RESPONSES SECTION (One-directional client-only submission channel) */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-indigo-400" />
                Client Comments & Responses
              </h3>
              <p className="text-xs text-slate-400">
                {isClientRole
                  ? "One-directional channel for you to provide responses, updates, and clarifications regarding Pending Items / Action Required."
                  : `One-directional channel for ${client?.name || "the client"} to respond to Pending Items. Staff accounts have read-only visibility.`}
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <span className="px-3 py-1 bg-slate-800 text-slate-300 border border-slate-700 rounded-full text-[11px] font-mono flex items-center gap-1.5">
                <Lock className="w-3 h-3 text-amber-400" />
                Client Response Channel ({comments.length})
              </span>
            </div>
          </div>

          {/* Feedback Banners */}
          {commentSuccessMsg && (
            <div className="p-3 bg-emerald-950/80 border border-emerald-700/80 rounded-xl text-xs text-emerald-300 flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{commentSuccessMsg}</span>
            </div>
          )}

          {commentError && (
            <div className="p-3 bg-rose-950/80 border border-rose-700/80 rounded-xl text-xs text-rose-300 flex items-center gap-2 animate-in fade-in">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{commentError}</span>
            </div>
          )}

          {/* Comments List */}
          <div className="space-y-3">
            {comments.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-1.5">
                <MessageCircle className="w-8 h-8 text-slate-700 mx-auto" />
                <p className="font-semibold text-slate-400">No client responses posted yet.</p>
                <p className="text-[11px] text-slate-500">
                  {isClientRole
                    ? "You can post responses, clarify questions, or notify staff when pending action items have been fulfilled."
                    : "When the client posts responses or comments regarding Pending Items, they will appear here."}
                </p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {comments.map((c) => {
                  const isCurrentUser = c.authorId === userProfile.uid;

                  return (
                    <div
                      key={c.id}
                      className="p-4 rounded-xl border bg-slate-950/90 border-slate-800 hover:border-slate-700 transition-all"
                    >
                      {/* Comment Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/60 pb-2 mb-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-white">
                            {c.authorName || "Client"}
                          </span>

                          {isCurrentUser && (
                            <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-300 rounded font-medium">
                              You
                            </span>
                          )}

                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold border bg-emerald-950 text-emerald-300 border-emerald-800">
                            Client Response
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
                          <Clock className="w-3 h-3 text-slate-500" />
                          <span>{formatCommentTimestamp(c.timestamp)}</span>
                        </div>
                      </div>

                      {/* Comment Body */}
                      <div className="text-xs sm:text-sm text-slate-200 whitespace-pre-line leading-relaxed">
                        {c.text}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* New Comment Submission Form: ONLY visible to client role */}
          {isClientRole ? (
            <form
              onSubmit={handlePostComment}
              className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <label
                  htmlFor="new-client-comment-textarea"
                  className="text-xs font-bold text-slate-300 flex items-center gap-1.5"
                >
                  <CornerDownRight className="w-3.5 h-3.5 text-indigo-400" />
                  Respond to Pending Items / Engagement Team
                </label>

                <span className="text-[11px] text-slate-400">
                  Posting as <strong className="text-slate-200">{userProfile.displayName || client?.name || userProfile.email}</strong> (Client)
                </span>
              </div>

              <textarea
                id="new-client-comment-textarea"
                required
                rows={3}
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Type your response, clarification, or notification for the audit team here... (append-only record)"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-y"
              />

              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
                <div className="text-[11px] text-slate-500 flex items-center gap-1">
                  <Lock className="w-3 h-3 text-amber-500/70" />
                  <span>Responses are permanent and cannot be edited or deleted once submitted.</span>
                </div>

                <button
                  type="submit"
                  disabled={postingComment || !commentText.trim()}
                  className={`px-5 py-2 text-xs font-bold rounded-xl shadow transition-all flex items-center gap-1.5 shrink-0 ${
                    !commentText.trim() || postingComment
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed opacity-60 border border-slate-700"
                      : "bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer shadow-indigo-900/40"
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  {postingComment ? "Submitting..." : "Submit Response"}
                </button>
              </div>
            </form>
          ) : (
            <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs text-slate-400 flex items-center gap-2.5">
              <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>
                <strong>One-Way Client Channel:</strong> This section is reserved exclusively for the client to submit responses to Pending Items. Staff accounts have read-only access here. To post internal staff discussion or partner queries, use the <strong>Review Notes</strong> section below.
              </span>
            </div>
          )}
        </div>

        {/* REVIEW NOTES SECTION (Strictly internal to full_admin & team_member — NEVER visible to client) */}
        {!isClientRole && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-purple-400" />
                  Review Notes (Internal Firm Exchange)
                </h3>
                <p className="text-xs text-slate-400">
                  Internal discussion and review exchange between Senior Partner (Admin) and assigned team members. Strictly confidential — never visible to clients.
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="px-3 py-1 bg-purple-950 text-purple-300 border border-purple-800 rounded-full text-[11px] font-mono flex items-center gap-1.5">
                  <ShieldAlert className="w-3 h-3 text-purple-400" />
                  Internal Staff Only ({reviewNotes.length})
                </span>
              </div>
            </div>

            {/* Feedback Banners */}
            {reviewNoteSuccessMsg && (
              <div className="p-3 bg-emerald-950/80 border border-emerald-700/80 rounded-xl text-xs text-emerald-300 flex items-center gap-2 animate-in fade-in">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{reviewNoteSuccessMsg}</span>
              </div>
            )}

            {reviewNoteError && (
              <div className="p-3 bg-rose-950/80 border border-rose-700/80 rounded-xl text-xs text-rose-300 flex items-center gap-2 animate-in fade-in">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{reviewNoteError}</span>
              </div>
            )}

            {/* Review Notes List */}
            <div className="space-y-3">
              {reviewNotes.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-1.5">
                  <MessageCircle className="w-8 h-8 text-slate-700 mx-auto" />
                  <p className="font-semibold text-slate-400">No internal review notes posted yet.</p>
                  <p className="text-[11px] text-slate-500">
                    Administrators and assigned team members can post confidential internal review comments, questions, and audit instructions below.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                  {reviewNotes.map((r) => {
                    const isCurrentUser = r.authorId === userProfile.uid;
                    const isAdminAuthor = r.authorRole === "full_admin";

                    return (
                      <div
                        key={r.id}
                        className={`p-4 rounded-xl border transition-all ${
                          isAdminAuthor
                            ? "bg-purple-950/20 border-purple-900/50 hover:border-purple-800/70"
                            : "bg-indigo-950/20 border-indigo-900/50 hover:border-indigo-800/70"
                        }`}
                      >
                        {/* Note Header */}
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/60 pb-2 mb-2.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs text-white">
                              {r.authorName || (isAdminAuthor ? "Senior Partner (Admin)" : "Audit Staff")}
                            </span>

                            {isCurrentUser && (
                              <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-300 rounded font-medium">
                                You
                              </span>
                            )}

                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                isAdminAuthor
                                  ? "bg-purple-950 text-purple-300 border-purple-800"
                                  : "bg-indigo-950 text-indigo-300 border-indigo-800"
                              }`}
                            >
                              {isAdminAuthor ? "Senior Partner (Admin)" : "Assigned Staff"}
                            </span>

                            {r.entryType && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                {r.entryType === "review_comment" ? "Review Comment" : r.entryType}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
                            <Clock className="w-3 h-3 text-slate-500" />
                            <span>{formatCommentTimestamp(r.timestamp)}</span>
                          </div>
                        </div>

                        {/* Note Body */}
                        <div className="text-xs sm:text-sm text-slate-200 whitespace-pre-line leading-relaxed">
                          {r.text}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* New Review Note Submission Form */}
            <form
              onSubmit={handlePostReviewNote}
              className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3"
            >
              <div className="flex items-center justify-between">
                <label
                  htmlFor="new-review-note-textarea"
                  className="text-xs font-bold text-slate-300 flex items-center gap-1.5"
                >
                  <CornerDownRight className="w-3.5 h-3.5 text-purple-400" />
                  Add Internal Review Note / Question
                </label>

                <span className="text-[11px] text-slate-400">
                  Posting as <strong className="text-slate-200">{userProfile.displayName || userProfile.email}</strong> ({userProfile.role === "full_admin" ? "Senior Partner" : "Team Member"})
                </span>
              </div>

              <textarea
                id="new-review-note-textarea"
                required
                rows={3}
                value={reviewNoteText}
                onChange={(e) => setReviewNoteText(e.target.value)}
                placeholder="Type internal review notes, questions, or instructions for the engagement team here... (never visible to client)"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 transition-colors resize-y"
              />

              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
                <div className="text-[11px] text-slate-500 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3 text-purple-400/80" />
                  <span>Confidential internal exchange between firm staff & partners.</span>
                </div>

                <button
                  type="submit"
                  disabled={postingReviewNote || !reviewNoteText.trim()}
                  className={`px-5 py-2 text-xs font-bold rounded-xl shadow transition-all flex items-center gap-1.5 shrink-0 ${
                    !reviewNoteText.trim() || postingReviewNote
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed opacity-60 border border-slate-700"
                      : "bg-purple-600 hover:bg-purple-500 text-white cursor-pointer shadow-purple-900/40"
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  {postingReviewNote ? "Posting..." : "Post Review Note"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
      )}

      {/* TEAM MEMBER ASSIGNMENT MODAL (Full Admin) */}
      {isAssignModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-white space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-400" />
                Manage Team Member Assignment
              </h3>
              <button
                type="button"
                onClick={() => setIsAssignModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Select team members / auditors who should have access and responsibility for this engagement folder.
            </p>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-medium">Available Staff (role: team_member)</span>
                {teamMembers.length > 0 && (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedAssigneeIds(teamMembers.map((t) => t.uid))}
                      className="text-indigo-400 hover:underline"
                    >
                      Select All
                    </button>
                    <span className="text-slate-600">|</span>
                    <button
                      type="button"
                      onClick={() => setSelectedAssigneeIds([])}
                      className="text-slate-400 hover:underline"
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>

              {teamMembers.length === 0 ? (
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                  No staff accounts with role <code>team_member</code> found in system directory.
                </div>
              ) : (
                <div className="max-h-56 overflow-y-auto space-y-2 bg-slate-950 border border-slate-800 p-3 rounded-xl">
                  {teamMembers.map((tm) => {
                    const isSelected = selectedAssigneeIds.includes(tm.uid);
                    return (
                      <label
                        key={tm.uid}
                        className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-all text-xs ${
                          isSelected
                            ? "bg-indigo-950/60 border-indigo-700 text-white"
                            : "bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {
                              if (isSelected) {
                                setSelectedAssigneeIds(selectedAssigneeIds.filter((id) => id !== tm.uid));
                              } else {
                                setSelectedAssigneeIds([...selectedAssigneeIds, tm.uid]);
                              }
                            }}
                            className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer"
                          />
                          <div>
                            <span className="font-semibold block text-slate-100">{tm.displayName || tm.email}</span>
                            <span className="text-[10px] text-slate-400 font-mono">{tm.email}</span>
                          </div>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {tm.role}
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsAssignModalOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={savingAssignment}
                onClick={handleSaveAssignment}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-lg shadow disabled:opacity-50 flex items-center gap-1.5"
              >
                {savingAssignment ? "Saving..." : "Save Assignment"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
