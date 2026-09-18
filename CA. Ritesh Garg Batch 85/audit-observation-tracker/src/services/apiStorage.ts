import { AuditType, Engagement, Observation, FirmProfile, ObservationStatus, AuditChecklistItem } from '../types/audit';
import { DEFAULT_AUDIT_TYPES, DEFAULT_FIRM_PROFILE } from './storage';

export { DEFAULT_AUDIT_TYPES, DEFAULT_FIRM_PROFILE };

class ApiStorageService {
  private async request<T>(url: string, options?: RequestInit): Promise<T> {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP error ${res.status}`);
    }
    return res.json();
  }

  // Audit Types
  async getAuditTypes(): Promise<AuditType[]> {
    return this.request<AuditType[]>('/api/audit-types');
  }

  async saveAuditType(type: Partial<AuditType> & { name: string; code: string }): Promise<AuditType> {
    if (type.id) {
      return this.request<AuditType>(`/api/audit-types/${type.id}`, {
        method: 'PUT',
        body: JSON.stringify(type),
      });
    }
    return this.request<AuditType>('/api/audit-types', {
      method: 'POST',
      body: JSON.stringify(type),
    });
  }

  async deleteAuditType(id: string): Promise<boolean> {
    await this.request<{ success: boolean }>(`/api/audit-types/${id}`, {
      method: 'DELETE',
    });
    return true;
  }

  // Engagements
  async getEngagements(): Promise<Engagement[]> {
    return this.request<Engagement[]>('/api/engagements');
  }

  async getEngagementById(id: string): Promise<Engagement | undefined> {
    try {
      return await this.request<Engagement>(`/api/engagements/${id}`);
    } catch {
      return undefined;
    }
  }

  async saveEngagement(eng: Partial<Engagement> & { clientName: string; auditTypeId: string; financialYear: string; engagementPartner?: string }): Promise<Engagement> {
    if (eng.id) {
      return this.request<Engagement>(`/api/engagements/${eng.id}`, {
        method: 'PUT',
        body: JSON.stringify(eng),
      });
    }
    return this.request<Engagement>('/api/engagements', {
      method: 'POST',
      body: JSON.stringify(eng),
    });
  }

  async deleteEngagement(id: string): Promise<boolean> {
    await this.request<{ success: boolean }>(`/api/engagements/${id}`, {
      method: 'DELETE',
    });
    return true;
  }

  async bulkAddEngagements(newEngagements: Engagement[]): Promise<number> {
    const res = await this.request<{ added: number }>('/api/engagements/bulk', {
      method: 'POST',
      body: JSON.stringify({ engagements: newEngagements }),
    });
    return res.added;
  }

  // Observations
  async getObservations(): Promise<Observation[]> {
    return this.request<Observation[]>('/api/observations');
  }

  async getObservationById(id: string): Promise<Observation | undefined> {
    try {
      return await this.request<Observation>(`/api/observations/${id}`);
    } catch {
      return undefined;
    }
  }

  async getObservationsByEngagementId(engagementId: string): Promise<Observation[]> {
    const all = await this.getObservations();
    return all.filter(o => o.engagementId === engagementId);
  }

  async saveObservation(obs: Partial<Observation> & { engagementId: string; description: string; severity: any; status: any }): Promise<Observation> {
    if (obs.id) {
      return this.request<Observation>(`/api/observations/${obs.id}`, {
        method: 'PUT',
        body: JSON.stringify(obs),
      });
    }
    return this.request<Observation>('/api/observations', {
      method: 'POST',
      body: JSON.stringify(obs),
    });
  }

  async updateObservationStatus(id: string, status: ObservationStatus): Promise<Observation | undefined> {
    return this.request<Observation>(`/api/observations/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async deleteObservation(id: string): Promise<boolean> {
    await this.request<{ success: boolean }>(`/api/observations/${id}`, {
      method: 'DELETE',
    });
    return true;
  }

  // Checklists Management
  async getChecklistItems(): Promise<AuditChecklistItem[]> {
    return this.request<AuditChecklistItem[]>('/api/checklist-items');
  }

  async saveChecklistItem(itemData: Partial<AuditChecklistItem> & { checkPoint: string; auditTypeId: string }): Promise<AuditChecklistItem> {
    if (itemData.id) {
      return this.request<AuditChecklistItem>(`/api/checklist-items/${itemData.id}`, {
        method: 'PUT',
        body: JSON.stringify(itemData),
      });
    }
    return this.request<AuditChecklistItem>('/api/checklist-items', {
      method: 'POST',
      body: JSON.stringify(itemData),
    });
  }

  async deleteChecklistItem(id: string): Promise<boolean> {
    await this.request<{ success: boolean }>(`/api/checklist-items/${id}`, {
      method: 'DELETE',
    });
    return true;
  }

  async bulkSaveChecklistItems(newItems: AuditChecklistItem[], replace = false): Promise<number> {
    const res = await this.request<{ count: number }>('/api/checklist-items/bulk', {
      method: 'POST',
      body: JSON.stringify({ items: newItems, replace }),
    });
    return res.count;
  }

  // Firm Profile
  async getFirmProfile(): Promise<FirmProfile> {
    return this.request<FirmProfile>('/api/firm-profile');
  }

  async saveFirmProfile(profile: FirmProfile): Promise<FirmProfile> {
    return this.request<FirmProfile>('/api/firm-profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  }

  // Reset / Backup / Restore
  async clearAllClientData(): Promise<void> {
    await this.request<{ success: boolean }>('/api/clear-client-data', {
      method: 'POST',
    });
  }

  async resetToSampleData(): Promise<void> {
    await this.request<{ success: boolean }>('/api/reset-sample-data', {
      method: 'POST',
    });
  }

  async exportAllDataJson(): Promise<string> {
    const data = await this.request<object>('/api/export/all');
    return JSON.stringify(data, null, 2);
  }

  async importDataJson(jsonStr: string): Promise<boolean> {
    try {
      const data = JSON.parse(jsonStr);
      await this.request<{ success: boolean }>('/api/import/all', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return true;
    } catch (e) {
      console.error('Failed to import JSON data:', e);
      return false;
    }
  }
}

export const apiStorageService = new ApiStorageService();
export const storageService = apiStorageService;
