import {
  InwardShipment,
  OutwardShipment,
  UserProfile,
  NotificationLog,
  ThemeStyle,
  IconConcept,
  UserRole,
  ShipmentStatus,
  Organization
} from '../types';
import {
  MOCK_ORGANIZATIONS,
  MOCK_USERS,
  INITIAL_INWARD,
  INITIAL_OUTWARD,
  INITIAL_NOTIFICATIONS
} from '../data/mockData';

const ORGANIZATIONS_STORAGE_KEY = 'ca_parceldesk_organizations_v2';
const USERS_STORAGE_KEY = 'ca_parceldesk_users_v2';
const INWARD_STORAGE_KEY = 'ca_parceldesk_inward_v2';
const OUTWARD_STORAGE_KEY = 'ca_parceldesk_outward_v2';
const NOTIFICATIONS_STORAGE_KEY = 'ca_parceldesk_notifications_v2';
const CURRENT_USER_KEY = 'ca_parceldesk_current_user_v2';
const CURRENT_THEME_KEY = 'ca_parceldesk_current_theme_v1';
const CURRENT_ICON_KEY = 'ca_parceldesk_current_icon_v1';

export class ParcelStorageService {
  // -------------------------------------------------------------
  // ORGANIZATIONS & MULTI-TENANCY MANAGEMENT
  // -------------------------------------------------------------
  static getAllOrganizations(): Organization[] {
    try {
      const data = localStorage.getItem(ORGANIZATIONS_STORAGE_KEY);
      if (data) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    localStorage.setItem(ORGANIZATIONS_STORAGE_KEY, JSON.stringify(MOCK_ORGANIZATIONS));
    return MOCK_ORGANIZATIONS;
  }

  static getOrganizationById(id?: string): Organization | undefined {
    const orgs = this.getAllOrganizations();
    if (!id) return orgs[0];
    return orgs.find((o) => o.id === id) || orgs[0];
  }

  static getOrganizationByCode(code: string): Organization | undefined {
    const orgs = this.getAllOrganizations();
    const clean = code.trim().toUpperCase();
    return orgs.find((o) => o.code.toUpperCase() === clean);
  }

  static registerOrganization(name: string, customCode?: string): Organization {
    const orgs = this.getAllOrganizations();
    const cleanName = name.trim();
    const existing = orgs.find((o) => o.name.toLowerCase() === cleanName.toLowerCase());
    if (existing) return existing;

    // Generate clean firm code
    const slug = cleanName
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 6) || 'FIRM';
    const randNum = Math.floor(100 + Math.random() * 900);
    const orgCode = customCode ? customCode.trim().toUpperCase() : `${slug}-${randNum}`;
    const orgId = `org_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    const newOrg: Organization = {
      id: orgId,
      name: cleanName,
      code: orgCode,
      createdAt: new Date().toISOString()
    };

    const updated = [...orgs, newOrg];
    localStorage.setItem(ORGANIZATIONS_STORAGE_KEY, JSON.stringify(updated));
    return newOrg;
  }

  static getActiveOrgId(): string {
    const currentUser = this.getCurrentUser();
    return currentUser.organizationId || 'org_singhania_ca';
  }

  // -------------------------------------------------------------
  // USER ACCOUNTS & RBAC (ORGANIZATION SCOPED)
  // -------------------------------------------------------------
  static getAllUsers(): UserProfile[] {
    try {
      const stored = localStorage.getItem(USERS_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(MOCK_USERS));
    return MOCK_USERS;
  }

  static getOrganizationUsers(orgId?: string): UserProfile[] {
    const targetOrgId = orgId || this.getActiveOrgId();
    const allUsers = this.getAllUsers();
    const filtered = allUsers.filter((u) => u.organizationId === targetOrgId);
    return filtered.length > 0 ? filtered : allUsers;
  }

  static registerUser(userData: {
    name: string;
    email: string;
    role: UserRole;
    department: string;
    designation: string;
    phone: string;
    firmName: string;
    organizationCode?: string;
    icaiNumber?: string;
  }): UserProfile {
    const allUsers = this.getAllUsers();
    let org: Organization;

    // If organizationCode was provided, try to find by code
    if (userData.organizationCode?.trim()) {
      const found = this.getOrganizationByCode(userData.organizationCode);
      if (found) {
        org = found;
      } else {
        org = this.registerOrganization(userData.firmName, userData.organizationCode);
      }
    } else {
      org = this.registerOrganization(userData.firmName);
    }

    const orgUsers = allUsers.filter((u) => u.organizationId === org.id);
    const newId = `USR-${org.code.slice(0, 4)}-${String(orgUsers.length + 1).padStart(2, '0')}`;

    const newUser: UserProfile = {
      id: newId,
      name: userData.name.trim(),
      email: userData.email.trim().toLowerCase(),
      role: userData.role,
      department: userData.department,
      designation: userData.designation,
      phone: userData.phone,
      firmName: org.name,
      organizationId: org.id,
      icaiNumber: userData.icaiNumber
    };

    const updatedUsers = [...allUsers, newUser];
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(updatedUsers));
    this.setCurrentUser(newUser);

    // Add welcome notification scoped to this organization
    this.addNotification({
      organizationId: org.id,
      recipient: newUser.name,
      channel: 'In-App',
      type: 'Account Created',
      referenceNumber: `AUTH-${newUser.id}`,
      trackingNumber: 'N/A',
      message: `🎉 Welcome to ParcelDesk, ${newUser.name}! Workstation ready for ${org.name} with firm code: ${org.code}.`
    });

    window.dispatchEvent(new CustomEvent('users_list_updated', { detail: this.getOrganizationUsers(org.id) }));
    return newUser;
  }

  static loginUser(emailOrId: string, _password?: string): UserProfile | null {
    const users = this.getAllUsers();
    const clean = emailOrId.trim().toLowerCase();
    const found = users.find(
      (u) =>
        u.email.toLowerCase() === clean ||
        u.id.toLowerCase() === clean ||
        u.name.toLowerCase() === clean
    );

    if (found) {
      this.setCurrentUser(found);
      return found;
    }
    return null;
  }

  static updateUserPassword(emailOrId: string, _newPassword: string): UserProfile | null {
    const users = this.getAllUsers();
    const clean = emailOrId.trim().toLowerCase();
    const index = users.findIndex(
      (u) =>
        u.email.toLowerCase() === clean ||
        u.id.toLowerCase() === clean ||
        u.name.toLowerCase() === clean
    );

    if (index !== -1) {
      const updatedUser = { ...users[index] };
      users[index] = updatedUser;
      localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));

      this.addNotification({
        organizationId: updatedUser.organizationId,
        recipient: updatedUser.name,
        channel: 'In-App',
        type: 'Account Created',
        referenceNumber: `SEC-${updatedUser.id}`,
        trackingNumber: 'N/A',
        message: `🔒 Workstation credentials updated successfully for ${updatedUser.name} on ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`
      });

      this.setCurrentUser(updatedUser);
      window.dispatchEvent(new CustomEvent('users_list_updated', { detail: this.getOrganizationUsers(updatedUser.organizationId) }));
      return updatedUser;
    }
    return null;
  }

  static updateUserProfile(userId: string, updates: Partial<UserProfile>): UserProfile | null {
    const users = this.getAllUsers();
    const index = users.findIndex((u) => u.id === userId);
    if (index === -1) return null;

    const current = users[index];
    const updatedUser: UserProfile = {
      ...current,
      ...updates,
      id: current.id,
      organizationId: current.organizationId
    };

    // If firm name changed, update organization name
    if (updates.firmName && updates.firmName !== current.firmName) {
      const orgs = this.getAllOrganizations();
      const orgIdx = orgs.findIndex((o) => o.id === current.organizationId);
      if (orgIdx !== -1) {
        orgs[orgIdx] = { ...orgs[orgIdx], name: updates.firmName };
        localStorage.setItem(ORGANIZATIONS_STORAGE_KEY, JSON.stringify(orgs));
      }
    }

    users[index] = updatedUser;
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));

    const activeUser = this.getCurrentUser();
    if (activeUser.id === userId) {
      this.setCurrentUser(updatedUser);
    }

    this.addNotification({
      organizationId: updatedUser.organizationId,
      recipient: updatedUser.name,
      channel: 'In-App',
      type: 'Account Created',
      referenceNumber: `PRF-${updatedUser.id}`,
      trackingNumber: 'N/A',
      message: `👤 Profile details & workstation permissions updated for ${updatedUser.name} (${updatedUser.designation}).`
    });

    window.dispatchEvent(new CustomEvent('users_list_updated', { detail: this.getOrganizationUsers(updatedUser.organizationId) }));
    return updatedUser;
  }

  static logoutUser(): void {
    localStorage.removeItem(CURRENT_USER_KEY);
    window.dispatchEvent(new CustomEvent('user_logged_out'));
  }

  static getCurrentUser(): UserProfile {
    try {
      const stored = localStorage.getItem(CURRENT_USER_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === 'object' && parsed.name) return parsed;
      }
    } catch {}
    const users = this.getAllUsers();
    const defaultUser = users[0] || MOCK_USERS[0];
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(defaultUser));
    return defaultUser;
  }

  static setCurrentUser(user: UserProfile): void {
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
    window.dispatchEvent(new CustomEvent('user_changed', { detail: user }));
    window.dispatchEvent(new CustomEvent('inward_updated', { detail: this.getInwardShipments(user.organizationId) }));
    window.dispatchEvent(new CustomEvent('outward_updated', { detail: this.getOutwardShipments(user.organizationId) }));
    window.dispatchEvent(new CustomEvent('notifications_updated', { detail: this.getNotifications(user.organizationId) }));
    window.dispatchEvent(new CustomEvent('users_list_updated', { detail: this.getOrganizationUsers(user.organizationId) }));
  }

  // -------------------------------------------------------------
  // INWARD SHIPMENT MANAGEMENT (ORGANIZATION SCOPED)
  // -------------------------------------------------------------
  static getAllInwardRaw(): InwardShipment[] {
    try {
      const data = localStorage.getItem(INWARD_STORAGE_KEY);
      if (data !== null) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch {}
    const seeded = INITIAL_INWARD.map((item) => ({
      ...item,
      organizationId: item.organizationId || 'org_singhania_ca'
    }));
    localStorage.setItem(INWARD_STORAGE_KEY, JSON.stringify(seeded));
    return seeded;
  }

  static getInwardShipments(orgId?: string): InwardShipment[] {
    const targetOrgId = orgId || this.getActiveOrgId() || 'org_singhania_ca';
    const all = this.getAllInwardRaw();
    return all.filter((item) => item.organizationId === targetOrgId || (!item.organizationId && targetOrgId === 'org_singhania_ca'));
  }

  static saveInwardShipments(shipmentsForOrg: InwardShipment[], orgId?: string): void {
    const targetOrgId = orgId || this.getActiveOrgId() || 'org_singhania_ca';
    const all = this.getAllInwardRaw();
    const others = all.filter((item) => item.organizationId && item.organizationId !== targetOrgId);
    const updatedAll = [...shipmentsForOrg, ...others];
    localStorage.setItem(INWARD_STORAGE_KEY, JSON.stringify(updatedAll));
    window.dispatchEvent(new CustomEvent('inward_updated', { detail: shipmentsForOrg }));
  }

  static addInwardShipment(
    shipment: Omit<InwardShipment, 'id' | 'referenceNumber' | 'events'>
  ): InwardShipment {
    const targetOrgId = shipment.organizationId || this.getActiveOrgId() || 'org_default';
    const orgList = this.getInwardShipments(targetOrgId);
    const count = orgList.length + 1;
    const refNum = `INW-${new Date().getFullYear()}-${String(840 + count).padStart(4, '0')}`;
    const id = `INW-${String(count).padStart(3, '0')}`;

    const currentUser = this.getCurrentUser();

    const newShipment: InwardShipment = {
      ...shipment,
      id,
      organizationId: targetOrgId,
      referenceNumber: refNum,
      events: [
        {
          id: `EV-${Date.now()}-1`,
          timestamp:
            new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
            ' ' +
            new Date().toLocaleDateString(),
          status: shipment.status,
          location: 'Reception / Security Desk',
          description: `Docket logged by ${currentUser?.name || 'Reception'} for ${shipment.recipientStaffName} (${shipment.shelfLocation}).`,
          actorName: currentUser?.name || 'Front Desk Staff',
          actorRole: currentUser?.role || 'front_desk'
        }
      ]
    };

    const updated = [newShipment, ...orgList];
    this.saveInwardShipments(updated, targetOrgId);

    // Scoped Notification
    this.addNotification({
      organizationId: targetOrgId,
      recipient: `${newShipment.recipientStaffName}`,
      channel: 'In-App',
      type: newShipment.confidentiality === 'urgent' ? 'Urgent Handover' : 'Inward Arrived',
      referenceNumber: newShipment.referenceNumber,
      trackingNumber: newShipment.trackingNumber,
      message: `📦 Inward parcel from ${newShipment.senderName} has arrived. Stored at [${newShipment.shelfLocation}].`
    });

    return newShipment;
  }

  static updateInwardStatus(
    id: string,
    status: ShipmentStatus,
    location: string,
    description: string,
    actorName: string,
    actorRole: UserRole,
    podData?: any
  ): InwardShipment | null {
    const targetOrgId = this.getActiveOrgId();
    if (!targetOrgId) return null;

    const list = this.getInwardShipments(targetOrgId);
    const index = list.findIndex(
      (item) => item.id === id || item.referenceNumber === id || item.trackingNumber === id
    );
    if (index === -1) return null;

    const target = list[index];
    const newEvent = {
      id: `EV-${Date.now()}`,
      timestamp:
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
        ' ' +
        new Date().toLocaleDateString(),
      status,
      location,
      description,
      actorName,
      actorRole
    };

    const updatedItem: InwardShipment = {
      ...target,
      status,
      events: [...target.events, newEvent],
      proofOfDelivery: podData ? { ...target.proofOfDelivery, ...podData } : target.proofOfDelivery,
      internalHandoverSignedAt:
        status === 'handed_over_to_staff' ? new Date().toLocaleString() : target.internalHandoverSignedAt,
      internalHandoverSignedBy:
        status === 'handed_over_to_staff'
          ? podData?.signerName || actorName
          : target.internalHandoverSignedBy
    };

    list[index] = updatedItem;
    this.saveInwardShipments(list, targetOrgId);

    if (status === 'handed_over_to_staff') {
      this.addNotification({
        organizationId: targetOrgId,
        recipient: `${updatedItem.recipientStaffName}`,
        channel: 'In-App',
        type: 'POD Delivered',
        referenceNumber: updatedItem.referenceNumber,
        trackingNumber: updatedItem.trackingNumber,
        message: `✅ Custody Handover Complete: Parcel collected by ${updatedItem.internalHandoverSignedBy || actorName}.`
      });
    }

    return updatedItem;
  }

  // -------------------------------------------------------------
  // OUTWARD SHIPMENT MANAGEMENT (ORGANIZATION SCOPED)
  // -------------------------------------------------------------
  static getAllOutwardRaw(): OutwardShipment[] {
    try {
      const data = localStorage.getItem(OUTWARD_STORAGE_KEY);
      if (data !== null) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch {}
    const seeded = INITIAL_OUTWARD.map((item) => ({
      ...item,
      organizationId: item.organizationId || 'org_singhania_ca'
    }));
    localStorage.setItem(OUTWARD_STORAGE_KEY, JSON.stringify(seeded));
    return seeded;
  }

  static getOutwardShipments(orgId?: string): OutwardShipment[] {
    const targetOrgId = orgId || this.getActiveOrgId() || 'org_singhania_ca';
    const all = this.getAllOutwardRaw();
    return all.filter((item) => item.organizationId === targetOrgId || (!item.organizationId && targetOrgId === 'org_singhania_ca'));
  }

  static saveOutwardShipments(shipmentsForOrg: OutwardShipment[], orgId?: string): void {
    const targetOrgId = orgId || this.getActiveOrgId() || 'org_singhania_ca';
    const all = this.getAllOutwardRaw();
    const others = all.filter((item) => item.organizationId && item.organizationId !== targetOrgId);
    const updatedAll = [...shipmentsForOrg, ...others];
    localStorage.setItem(OUTWARD_STORAGE_KEY, JSON.stringify(updatedAll));
    window.dispatchEvent(new CustomEvent('outward_updated', { detail: shipmentsForOrg }));
  }

  static addOutwardShipment(
    shipment: Omit<OutwardShipment, 'id' | 'referenceNumber' | 'events'>
  ): OutwardShipment {
    const targetOrgId = shipment.organizationId || this.getActiveOrgId() || 'org_default';
    const orgList = this.getOutwardShipments(targetOrgId);
    const count = orgList.length + 1;
    const refNum = `OUT-${new Date().getFullYear()}-${String(420 + count).padStart(4, '0')}`;
    const id = `OUT-${String(count).padStart(3, '0')}`;

    const currentUser = this.getCurrentUser();

    const newShipment: OutwardShipment = {
      ...shipment,
      id,
      organizationId: targetOrgId,
      referenceNumber: refNum,
      events: [
        {
          id: `EV-${Date.now()}-10`,
          timestamp:
            new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
            ' ' +
            new Date().toLocaleDateString(),
          status: shipment.status,
          location: 'Dispatch Desk',
          description: `Dispatch logged for ${shipment.recipientName} (${shipment.clientName}). Carrier: ${shipment.carrier} AWB #${shipment.trackingNumber}.`,
          actorName: currentUser?.name || shipment.assignedStaffName,
          actorRole: currentUser?.role || 'audit_staff'
        }
      ]
    };

    const updated = [newShipment, ...orgList];
    this.saveOutwardShipments(updated, targetOrgId);

    // Scoped Notification
    this.addNotification({
      organizationId: targetOrgId,
      recipient: shipment.recipientEmail || shipment.recipientName,
      channel: 'Email',
      type: 'Outward Dispatched',
      referenceNumber: newShipment.referenceNumber,
      trackingNumber: newShipment.trackingNumber,
      message: `Your document (${newShipment.contentDescription}) has been dispatched via ${newShipment.carrier} (AWB #${newShipment.trackingNumber}).`
    });

    return newShipment;
  }

  static updateOutwardStatus(
    id: string,
    status: ShipmentStatus,
    location: string,
    description: string,
    actorName: string,
    actorRole: UserRole,
    podData?: any
  ): OutwardShipment | null {
    const targetOrgId = this.getActiveOrgId();
    if (!targetOrgId) return null;

    const list = this.getOutwardShipments(targetOrgId);
    const index = list.findIndex(
      (item) => item.id === id || item.referenceNumber === id || item.trackingNumber === id
    );
    if (index === -1) return null;

    const target = list[index];
    const newEvent = {
      id: `EV-${Date.now()}`,
      timestamp:
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
        ' ' +
        new Date().toLocaleDateString(),
      status,
      location,
      description,
      actorName,
      actorRole
    };

    const updatedItem: OutwardShipment = {
      ...target,
      status,
      events: [...target.events, newEvent],
      proofOfDelivery: podData ? { ...target.proofOfDelivery, ...podData } : target.proofOfDelivery
    };

    list[index] = updatedItem;
    this.saveOutwardShipments(list, targetOrgId);

    if (status === 'delivered') {
      this.addNotification({
        organizationId: targetOrgId,
        recipient: `${updatedItem.assignedStaffName} (Assigned Staff)`,
        channel: 'In-App',
        type: 'POD Delivered',
        referenceNumber: updatedItem.referenceNumber,
        trackingNumber: updatedItem.trackingNumber,
        message: `🎯 Delivery Confirmed: Outbound parcel ${updatedItem.referenceNumber} to ${updatedItem.recipientName} delivered successfully.`
      });
    }

    return updatedItem;
  }

  // -------------------------------------------------------------
  // SEARCH (ORGANIZATION SCOPED)
  // -------------------------------------------------------------
  static searchShipments(query: string, orgId?: string): { inward: InwardShipment[]; outward: OutwardShipment[] } {
    const clean = query.trim().toLowerCase();
    if (!clean) return { inward: [], outward: [] };

    const inward = this.getInwardShipments(orgId).filter(
      (item) =>
        item.trackingNumber.toLowerCase().includes(clean) ||
        item.referenceNumber.toLowerCase().includes(clean) ||
        item.senderName.toLowerCase().includes(clean) ||
        item.recipientStaffName.toLowerCase().includes(clean) ||
        item.shelfLocation.toLowerCase().includes(clean) ||
        item.carrier.toLowerCase().includes(clean)
    );

    const outward = this.getOutwardShipments(orgId).filter(
      (item) =>
        item.trackingNumber.toLowerCase().includes(clean) ||
        item.referenceNumber.toLowerCase().includes(clean) ||
        item.clientName.toLowerCase().includes(clean) ||
        item.clientJobCode.toLowerCase().includes(clean) ||
        item.recipientName.toLowerCase().includes(clean) ||
        item.assignedStaffName.toLowerCase().includes(clean) ||
        item.carrier.toLowerCase().includes(clean)
    );

    return { inward, outward };
  }

  // -------------------------------------------------------------
  // NOTIFICATIONS (ORGANIZATION SCOPED)
  // -------------------------------------------------------------
  static getAllNotificationsRaw(): NotificationLog[] {
    try {
      const data = localStorage.getItem(NOTIFICATIONS_STORAGE_KEY);
      if (data !== null) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch {}
    const seeded = INITIAL_NOTIFICATIONS.map((item) => ({
      ...item,
      organizationId: item.organizationId || 'org_singhania_ca'
    }));
    localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(seeded));
    return seeded;
  }

  static getNotifications(orgId?: string): NotificationLog[] {
    const targetOrgId = orgId || this.getActiveOrgId() || 'org_singhania_ca';
    const all = this.getAllNotificationsRaw();
    return all.filter((item) => item.organizationId === targetOrgId || (!item.organizationId && targetOrgId === 'org_singhania_ca'));
  }

  static markNotificationAsRead(id: string): void {
    const all = this.getAllNotificationsRaw();
    const updated = all.map((item) => (item.id === id ? { ...item, status: 'Read' as const } : item));
    localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(
      new CustomEvent('notifications_updated', { detail: this.getNotifications() })
    );
  }

  static markAllNotificationsAsRead(): void {
    const targetOrgId = this.getActiveOrgId();
    if (!targetOrgId) return;
    const all = this.getAllNotificationsRaw();
    const updated = all.map((item) =>
      item.organizationId === targetOrgId ? { ...item, status: 'Read' as const } : item
    );
    localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(
      new CustomEvent('notifications_updated', { detail: this.getNotifications(targetOrgId) })
    );
  }

  static addNotification(
    notif: Omit<NotificationLog, 'id' | 'timestamp' | 'status'>
  ): void {
    const targetOrgId = notif.organizationId || this.getActiveOrgId() || 'org_default';
    const all = this.getAllNotificationsRaw();
    const newLog: NotificationLog = {
      ...notif,
      organizationId: targetOrgId,
      id: `NOTIF-${Date.now()}`,
      timestamp:
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
        ' ' +
        new Date().toLocaleDateString(),
      status: 'Sent'
    };
    const updated = [newLog, ...all];
    localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(
      new CustomEvent('notifications_updated', { detail: this.getNotifications(targetOrgId) })
    );
  }

  // -------------------------------------------------------------
  // THEME & BRANDING SETTINGS
  // -------------------------------------------------------------
  static getTheme(): ThemeStyle {
    return (localStorage.getItem(CURRENT_THEME_KEY) as ThemeStyle) || 'navy';
  }

  static setTheme(theme: ThemeStyle): void {
    localStorage.setItem(CURRENT_THEME_KEY, theme);
    window.dispatchEvent(new CustomEvent('theme_changed', { detail: theme }));
  }

  static getIconConcept(): IconConcept {
    const icon = localStorage.getItem(CURRENT_ICON_KEY) as IconConcept;
    if (icon && icon === 'parceldesk_official') {
      return icon;
    }
    if (!icon || icon === 'flow_arrows' || icon === 'dynamic_cube') {
      localStorage.setItem(CURRENT_ICON_KEY, 'parceldesk_official');
      return 'parceldesk_official';
    }
    return icon;
  }

  static setIconConcept(icon: IconConcept): void {
    localStorage.setItem(CURRENT_ICON_KEY, icon);
    window.dispatchEvent(new CustomEvent('icon_changed', { detail: icon }));
  }

  // -------------------------------------------------------------
  // DATA RESET & CLEAR (TESTING & FRESH TESTING SUPPORT)
  // -------------------------------------------------------------
  static clearAllCouriers(): void {
    const orgId = this.getActiveOrgId() || 'org_singhania_ca';
    this.saveInwardShipments([], orgId);
    this.saveOutwardShipments([], orgId);
    localStorage.setItem(INWARD_STORAGE_KEY, JSON.stringify([]));
    localStorage.setItem(OUTWARD_STORAGE_KEY, JSON.stringify([]));

    window.dispatchEvent(new CustomEvent('inward_updated', { detail: [] }));
    window.dispatchEvent(new CustomEvent('outward_updated', { detail: [] }));
  }

  static resetToDefault(): void {
    this.clearAllCouriers();
  }
}
