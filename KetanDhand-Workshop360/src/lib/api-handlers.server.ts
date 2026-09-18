import { supabaseAdmin } from "@/integrations/supabase/client.server";

// Loosely typed admin client: these tables are only touched from this server-only module.
/* eslint-disable @typescript-eslint/no-explicit-any */
import type { Repair, RepairItem, User } from "@/types";

const db = supabaseAdmin as any;

export type ApiRequest = {
  path: string;
  method: string;
  body?: unknown;
  token?: string | null;
};

export type ApiResponse = {
  status: number;
  body: unknown;
};

const ok = (body: unknown): ApiResponse => ({ status: 200, body });
const fail = (status: number, error: string): ApiResponse => ({ status, body: { error } });

type UserRow = {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  role: User["role"];
  status: User["status"];
  created_at: string;
};

type RepairRow = {
  id: string;
  repair_no: string;
  bike_registration: string;
  bike_model: string;
  customer_name: string;
  customer_phone: string;
  mechanic_id: string | null;
  mechanic_name: string;
  start_time: string;
  completion_time: string | null;
  status: Repair["status"];
  items: RepairItem[];
  labour_charges: number;
  discount: number;
  tax_rate: number;
  audit_trail: Repair["auditTrail"];
  created_at: string;
};

const USER_COLS = "id, name, phone, email, role, status, created_at";

function toUser(row: UserRow): User {
  return {
    id: row.id,
    name: row.name,
    phone: row.phone,
    ...(row.email ? { email: row.email } : {}),
    role: row.role,
    status: row.status,
    createdAt: row.created_at,
  };
}

function toRepair(row: RepairRow): Repair {
  return {
    id: row.id,
    repairNo: row.repair_no,
    bikeRegistration: row.bike_registration,
    bikeModel: row.bike_model,
    customerName: row.customer_name,
    customerPhone: row.customer_phone,
    mechanicId: row.mechanic_id ?? "",
    mechanicName: row.mechanic_name,
    startTime: row.start_time,
    ...(row.completion_time ? { completionTime: row.completion_time } : {}),
    status: row.status,
    items: Array.isArray(row.items) ? row.items : [],
    labourCharges: Number(row.labour_charges),
    discount: Number(row.discount),
    taxRate: Number(row.tax_rate),
    auditTrail: Array.isArray(row.audit_trail) ? row.audit_trail : [],
    createdAt: row.created_at,
  };
}

function audit(userName: string, userRole: string, action: string, details: string) {
  return {
    id: `aud-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
    timestamp: new Date().toISOString(),
    userName,
    userRole,
    action,
    details,
  };
}

async function getSessionUser(token?: string | null): Promise<User | null> {
  if (!token) return null;
  const { data } = await db
    .from("app_sessions")
    .select("user_id, expires_at")
    .eq("token", token)
    .maybeSingle();
  if (!data || new Date(data.expires_at as string).getTime() < Date.now()) return null;
  const { data: user } = await db
    .from("app_users")
    .select(USER_COLS)
    .eq("id", data.user_id as string)
    .maybeSingle();
  if (!user) return null;
  const u = toUser(user as unknown as UserRow);
  return u.status === "approved" ? u : null;
}

function isManager(user: User) {
  return user.role === "owner" || user.role === "shopkeeper";
}

async function loadRepair(id: string) {
  const { data } = await db.from("repairs").select("*").eq("id", id).maybeSingle();
  return data ? (data as unknown as RepairRow) : null;
}

async function saveRepair(id: string, patch: Record<string, unknown>) {
  const { data, error } = await db
    .from("repairs")
    .update(patch)
    .eq("id", id)
    .select("*")
    .single();
  if (error) throw new Error(error.message);
  return toRepair(data as unknown as RepairRow);
}

export async function handleApi(req: ApiRequest): Promise<ApiResponse> {
  const { path, method } = req;
  const body = (req.body ?? {}) as any;
  const url = new URL(path, "http://local");
  const p = url.pathname;
  const query = url.searchParams;

  // ---------- Public auth routes ----------
  if (p === "/api/auth/status" && method === "GET") {
    const { count: ownerCount } = await db
      .from("app_users")
      .select("id", { count: "exact", head: true })
      .eq("role", "owner")
      .eq("status", "approved");
    const { count: userCount } = await db
      .from("app_users")
      .select("id", { count: "exact", head: true });
    return ok({ hasOwner: (ownerCount ?? 0) > 0, userCount: userCount ?? 0 });
  }

  if (p === "/api/auth/register" && method === "POST") {
    const { name, phone, email, password, confirmPassword, role: requestedRole } = body;
    if (!name || !phone || !password) return fail(400, "Name, phone and password are required.");
    if (password !== confirmPassword) return fail(400, "Passwords do not match.");
    if (String(password).length < 4) return fail(400, "Password must be at least 4 characters.");

    const { data: existing } = await db
      .from("app_users")
      .select("id")
      .or(email ? `phone.eq.${phone},email.eq.${email}` : `phone.eq.${phone}`)
      .maybeSingle();
    if (existing) return fail(400, "User with this phone or email already registered.");

    const { count: ownerCount } = await db
      .from("app_users")
      .select("id", { count: "exact", head: true })
      .eq("role", "owner");
    const isFirstUser = (ownerCount ?? 0) === 0;
    const role = isFirstUser ? "owner" : requestedRole === "shopkeeper" ? "shopkeeper" : "mechanic";
    const status = isFirstUser ? "approved" : "pending";

    const { data: created, error } = await db
      .rpc("create_app_user", {
        _name: name,
        _phone: phone,
        _email: email || null,
        _password: password,
        _role: role,
        _status: status,
      })
      .single();
    if (error) return fail(400, error.message);

    const registered = toUser(created as unknown as UserRow);
    let token: string | undefined;
    if (registered.status === "approved") {
      token = crypto.randomUUID() + crypto.randomUUID();
      await db.from("app_sessions").insert({ token, user_id: registered.id });
    }

    return ok({
      user: registered,
      ...(token ? { token } : {}),
      message: isFirstUser
        ? "Registered as Owner successfully."
        : "Registered successfully. Waiting for owner approval.",
    });
  }

  if (p === "/api/auth/login" && method === "POST") {
    const { identifier, password } = body;
    if (!identifier || !password) return fail(400, "Phone/Email and password are required.");

    const { data: verified, error } = await db
      .rpc("verify_app_user", { _identifier: String(identifier).trim(), _password: String(password) })
      .maybeSingle();
    if (error) return fail(500, error.message);
    if (!verified) return fail(401, "Invalid credentials.");

    const user = toUser(verified as unknown as UserRow);
    if (user.status === "deactivated")
      return fail(403, "Your account has been deactivated. Please contact the workshop owner.");
    if (user.status === "pending")
      return fail(403, "Your account is pending approval from the workshop owner.");
    if (user.status === "rejected")
      return fail(403, "Your registration was rejected by the workshop owner.");

    const token = crypto.randomUUID() + crypto.randomUUID();
    await db.from("app_sessions").insert({ token, user_id: user.id });
    return ok({ user, token });
  }

  // ---------- Everything below requires a session ----------
  const currentUser = await getSessionUser(req.token);
  if (!currentUser) return fail(401, "Your session has expired. Please sign in again.");

  if (p === "/api/auth/logout" && method === "POST") {
    if (req.token) await db.from("app_sessions").delete().eq("token", req.token);
    return ok({ message: "Signed out." });
  }

  if (p === "/api/auth/me" && method === "GET") return ok({ user: currentUser });

  // ---------- Users ----------
  if (p === "/api/users" && method === "GET") {
    const { data } = await db
      .from("app_users")
      .select(USER_COLS)
      .order("created_at", { ascending: true });
    return ok(((data ?? []) as unknown as unknown as UserRow[]).map(toUser));
  }

  const userStatusMatch = p.match(/^\/api\/users\/([^/]+)\/status$/);
  if (userStatusMatch && method === "PATCH") {
    if (!isManager(currentUser)) return fail(403, "Only the owner can change account status.");
    const { data, error } = await db
      .from("app_users")
      .update({ status: body.status })
      .eq("id", userStatusMatch[1]!)
      .select(USER_COLS)
      .maybeSingle();
    if (error) return fail(400, error.message);
    if (!data) return fail(404, "User not found");
    return ok(toUser(data as unknown as UserRow));
  }

  const userPasswordMatch = p.match(/^\/api\/users\/([^/]+)\/password$/);
  if (userPasswordMatch && method === "PATCH") {
    const targetId = userPasswordMatch[1]!;
    if (!isManager(currentUser) && currentUser.id !== targetId)
      return fail(403, "Only the owner can reset another user's password.");
    const { newPassword } = body;
    if (!newPassword || String(newPassword).length < 4)
      return fail(400, "Password must be at least 4 characters.");
    const { error } = await db.rpc("set_app_user_password", {
      _user_id: targetId,
      _password: String(newPassword),
    });
    if (error) return fail(400, error.message);
    return ok({ message: "Password updated successfully." });
  }

  const userMatch = p.match(/^\/api\/users\/([^/]+)$/);
  if (userMatch && method === "DELETE") {
    if (currentUser.role !== "owner") return fail(403, "Only the owner can remove a login.");
    const { data: target } = await db
      .from("app_users")
      .select("id, role")
      .eq("id", userMatch[1]!)
      .maybeSingle();
    if (!target) return fail(404, "User not found");
    if ((target as { role: string }).role === "owner") return fail(400, "Cannot delete owner account.");
    await db.from("app_users").delete().eq("id", userMatch[1]!);
    return ok({ message: "User login removed successfully." });
  }

  if (p === "/api/users/shopkeeper" && method === "POST") {
    if (!isManager(currentUser)) return fail(403, "Only the owner can create shopkeeper logins.");
    const { name, phone, email, password, confirmPassword } = body;
    if (!name || !phone || !password) return fail(400, "Name, phone and password are required.");
    if (password !== confirmPassword) return fail(400, "Passwords do not match.");

    const { data: existing } = await db
      .from("app_users")
      .select("id")
      .eq("phone", phone)
      .maybeSingle();
    if (existing) return fail(400, "User with this phone or email already registered.");

    const { data: created, error } = await db
      .rpc("create_app_user", {
        _name: name,
        _phone: phone,
        _email: email || null,
        _password: password,
        _role: "shopkeeper",
        _status: "pending",
      })
      .single();
    if (error) return fail(400, error.message);
    return ok({
      user: toUser(created as unknown as UserRow),
      message: "Shopkeeper account created successfully. Waiting for owner approval.",
    });
  }

  // ---------- Repairs ----------
  if (p === "/api/repairs" && method === "GET") {
    const { data } = await db
      .from("repairs")
      .select("*")
      .order("created_at", { ascending: false });
    return ok(((data ?? []) as unknown as RepairRow[]).map(toRepair));
  }

  if (p === "/api/repairs" && method === "POST") {
    const { bikeRegistration, bikeModel, customerName, customerPhone, mechanicId, mechanicName } = body;
    if (!bikeRegistration || !bikeModel || !mechanicId)
      return fail(400, "Bike registration, model and mechanic are required.");

    const repairNo = `REP-${Math.floor(100 + Math.random() * 900)}`;
    const now = new Date().toISOString();
    const { data, error } = await db
      .from("repairs")
      .insert({
        repair_no: repairNo,
        bike_registration: String(bikeRegistration).toUpperCase().trim(),
        bike_model: bikeModel,
        customer_name: customerName || "",
        customer_phone: customerPhone || "",
        mechanic_id: mechanicId,
        mechanic_name: mechanicName || "",
        start_time: now,
        status: "repairing",
        items: [],
        audit_trail: [
          audit(
            mechanicName || currentUser.name,
            "mechanic",
            "START_REPAIR",
            `Started repair for ${bikeModel} (${bikeRegistration})`,
          ),
        ],
      })
      .select("*")
      .single();
    if (error) return fail(400, error.message);
    return ok(toRepair(data as unknown as RepairRow));
  }

  const itemsMatch = p.match(/^\/api\/repairs\/([^/]+)\/items$/);
  if (itemsMatch && method === "POST") {
    const repair = await loadRepair(itemsMatch[1]!);
    if (!repair) return fail(404, "Repair not found");
    if (repair.status !== "repairing" && currentUser.role === "mechanic")
      return fail(403, "Cannot add items after repair is finished.");

    const { name, quantity } = body;
    if (!name || !quantity) return fail(400, "Product name and quantity are required.");

    const newItem: RepairItem = {
      id: `item-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      name: String(name).trim(),
      quantity: Number(quantity),
      rate: 0,
      addedBy: currentUser.role === "mechanic" ? "mechanic" : "owner",
      addedByName: currentUser.name,
      timestamp: new Date().toISOString(),
    };

    return ok(
      await saveRepair(repair.id, {
        items: [...repair.items, newItem],
        audit_trail: [
          ...repair.audit_trail,
          audit(
            currentUser.name,
            currentUser.role,
            "ADD_ITEM",
            `${currentUser.name} added ${newItem.name} × ${newItem.quantity}`,
          ),
        ],
      }),
    );
  }

  const itemMatch = p.match(/^\/api\/repairs\/([^/]+)\/items\/([^/]+)$/);
  if (itemMatch && (method === "PUT" || method === "DELETE")) {
    const repair = await loadRepair(itemMatch[1]!);
    if (!repair) return fail(404, "Repair not found");
    if (repair.status !== "repairing" && currentUser.role === "mechanic")
      return fail(403, "Mechanic cannot change items after repair is finished.");

    const items = [...repair.items];
    const index = items.findIndex((i) => i.id === itemMatch[2]!);
    if (index === -1) return fail(404, "Item not found");

    if (method === "DELETE") {
      const removed = items.splice(index, 1)[0]!;
      return ok(
        await saveRepair(repair.id, {
          items,
          audit_trail: [
            ...repair.audit_trail,
            audit(
              currentUser.name,
              currentUser.role,
              "DELETE_ITEM",
              `${currentUser.name} removed ${removed.name} × ${removed.quantity}`,
            ),
          ],
        }),
      );
    }

    const item = { ...items[index]! };
    const { name, quantity, rate } = body;
    const changes: string[] = [];
    if (name && name !== item.name) {
      changes.push(`name '${item.name}' → '${name}'`);
      item.name = String(name).trim();
    }
    if (quantity !== undefined && Number(quantity) !== item.quantity) {
      changes.push(`qty ${item.quantity} → ${quantity}`);
      item.quantity = Number(quantity);
    }
    if (rate !== undefined && isManager(currentUser) && Number(rate) !== item.rate) {
      changes.push(`rate ₹${item.rate} → ₹${rate}`);
      item.rate = Number(rate);
    }
    items[index] = item;

    return ok(
      await saveRepair(repair.id, {
        items,
        audit_trail: changes.length
          ? [
              ...repair.audit_trail,
              audit(
                currentUser.name,
                currentUser.role,
                "EDIT_ITEM",
                `${currentUser.name} updated ${item.name}: ${changes.join(", ")}`,
              ),
            ]
          : repair.audit_trail,
      }),
    );
  }

  const finishMatch = p.match(/^\/api\/repairs\/([^/]+)\/finish$/);
  if (finishMatch && method === "POST") {
    const repair = await loadRepair(finishMatch[1]!);
    if (!repair) return fail(404, "Repair not found");
    return ok(
      await saveRepair(repair.id, {
        status: "ready_for_billing",
        completion_time: new Date().toISOString(),
        audit_trail: [
          ...repair.audit_trail,
          audit(
            currentUser.name,
            currentUser.role,
            "FINISH_REPAIR",
            `${currentUser.name} marked repair as Ready for Billing`,
          ),
        ],
      }),
    );
  }

  const billingMatch = p.match(/^\/api\/repairs\/([^/]+)\/billing$/);
  if (billingMatch && method === "PUT") {
    if (!isManager(currentUser)) return fail(403, "Only the owner can update billing.");
    const repair = await loadRepair(billingMatch[1]!);
    if (!repair) return fail(404, "Repair not found");

    const labour = body.labourCharges !== undefined ? Number(body.labourCharges) : Number(repair.labour_charges);
    const discount = body.discount !== undefined ? Number(body.discount) : Number(repair.discount);
    const taxRate = body.taxRate !== undefined ? Number(body.taxRate) : Number(repair.tax_rate);

    return ok(
      await saveRepair(repair.id, {
        labour_charges: labour,
        discount,
        tax_rate: taxRate,
        items: Array.isArray(body.items) ? body.items : repair.items,
        audit_trail: [
          ...repair.audit_trail,
          audit(
            currentUser.name,
            currentUser.role,
            "UPDATE_BILLING",
            `${currentUser.name} updated billing (Labour: ₹${labour}, Discount: ₹${discount}, Tax: ${taxRate}%)`,
          ),
        ],
      }),
    );
  }

  const completeMatch = p.match(/^\/api\/repairs\/([^/]+)\/complete$/);
  if (completeMatch && method === "POST") {
    if (!isManager(currentUser)) return fail(403, "Only the owner can complete billing.");
    const repair = await loadRepair(completeMatch[1]!);
    if (!repair) return fail(404, "Repair not found");
    return ok(
      await saveRepair(repair.id, {
        status: "completed",
        completion_time: repair.completion_time ?? new Date().toISOString(),
        audit_trail: [
          ...repair.audit_trail,
          audit(
            currentUser.name,
            currentUser.role,
            "COMPLETE_REPAIR",
            `${currentUser.name} finalized and completed billing for repair ${repair.repair_no}`,
          ),
        ],
      }),
    );
  }

  // ---------- Bike history ----------
  const historyMatch = p.match(/^\/api\/bikes\/([^/]+)\/history$/);
  if (historyMatch && method === "GET") {
    const reg = decodeURIComponent(historyMatch[1]!).toUpperCase().trim();
    const { data } = await db
      .from("repairs")
      .select("*")
      .eq("bike_registration", reg)
      .order("created_at", { ascending: false });
    return ok(((data ?? []) as unknown as RepairRow[]).map(toRepair));
  }

  // ---------- Suggestions ----------
  if (p === "/api/suggestions" && method === "GET") {
    const { data } = await db.from("repairs").select("items");
    const productCounts = new Map<string, number>();
    const recent: { name: string; timestamp: string }[] = [];
    ((data ?? []) as { items: RepairItem[] }[]).forEach((r) => {
      (r.items ?? []).forEach((i) => {
        productCounts.set(i.name, (productCounts.get(i.name) ?? 0) + 1);
        recent.push({ name: i.name, timestamp: i.timestamp });
      });
    });
    recent.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    const uniqueRecent = Array.from(new Set(recent.map((i) => i.name)));
    const frequent = Array.from(productCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([name]) => name);
    const defaults = [
      "Gulf Engine Oil 20W-50",
      "Castrol Activ",
      "Total Engine Oil",
      "Oil Filter",
      "Brake Pad",
      "Spark Plug",
      "Chain Sprocket Set",
      "Clutch Plate",
      "Air Filter",
      "Headlight Bulb",
    ];
    return ok(Array.from(new Set([...uniqueRecent, ...frequent, ...defaults])));
  }

  // ---------- Analytics ----------
  if (p === "/api/analytics" && method === "GET") {
    const filter = query.get("filter") ?? "all";
    const { data } = await db.from("repairs").select("*");
    const all = ((data ?? []) as unknown as RepairRow[]).map(toRepair);
    const now = Date.now();

    let repairs = all;
    if (filter === "today") {
      const today = new Date().toDateString();
      repairs = all.filter((r) => new Date(r.startTime).toDateString() === today);
    } else if (filter === "week") {
      repairs = all.filter((r) => new Date(r.startTime).getTime() >= now - 7 * 86400000);
    } else if (filter === "month") {
      repairs = all.filter((r) => new Date(r.startTime).getTime() >= now - 30 * 86400000);
    } else if (filter === "custom") {
      const fromRaw = query.get("from");
      const toRaw = query.get("to");
      const fromTs = fromRaw ? new Date(`${fromRaw}T00:00:00`).getTime() : Number.NEGATIVE_INFINITY;
      const toTs = toRaw ? new Date(`${toRaw}T23:59:59.999`).getTime() : Number.POSITIVE_INFINITY;
      repairs = all.filter((r) => {
        const t = new Date(r.startTime).getTime();
        return t >= fromTs && t <= toTs;
      });
    }


    const tally = (entries: [string, number][], limit = 5) =>
      entries.sort((a, b) => b[1] - a[1]).slice(0, limit);

    const bikeCounts: Record<string, number> = {};
    const productCounts: Record<string, number> = {};
    const brandCounts: Record<string, number> = {};
    const mechanicCounts: Record<string, number> = {};
    const modelCounts: Record<string, number> = {};

    repairs.forEach((r) => {
      bikeCounts[r.bikeRegistration] = (bikeCounts[r.bikeRegistration] ?? 0) + 1;
      modelCounts[r.bikeModel] = (modelCounts[r.bikeModel] ?? 0) + 1;
      mechanicCounts[r.mechanicName] = (mechanicCounts[r.mechanicName] ?? 0) + 1;
      r.items.forEach((i) => {
        productCounts[i.name] = (productCounts[i.name] ?? 0) + i.quantity;
        const brand = i.name.split(" ")[0] || "Other";
        brandCounts[brand] = (brandCounts[brand] ?? 0) + i.quantity;
      });
    });

    const workload: Record<string, number> = {};
    all
      .filter((r) => r.status === "repairing")
      .forEach((r) => {
        workload[r.mechanicName] = (workload[r.mechanicName] ?? 0) + 1;
      });

    let totalMinutes = 0;
    let completed = 0;
    repairs.forEach((r) => {
      if (r.completionTime && r.startTime) {
        const diff = new Date(r.completionTime).getTime() - new Date(r.startTime).getTime();
        if (diff > 0) {
          totalMinutes += diff / 60000;
          completed++;
        }
      }
    });

    return ok({
      returningBikes: tally(Object.entries(bikeCounts)).map(([reg, count]) => ({ reg, count })),
      topProducts: tally(Object.entries(productCounts)).map(([name, count]) => ({ name, count })),
      topBrands: tally(Object.entries(brandCounts)).map(([brand, count]) => ({ brand, count })),
      repairsByMechanic: Object.entries(mechanicCounts).map(([name, count]) => ({ name, count })),
      currentWorkload: Object.entries(workload).map(([name, count]) => ({ name, count })),
      topModels: tally(Object.entries(modelCounts)).map(([model, count]) => ({ model, count })),
      avgCompletionTimeMinutes: completed > 0 ? Math.round(totalMinutes / completed) : 0,
      totalRepairs: repairs.length,
    });
  }

  return fail(404, "Not found");
}
