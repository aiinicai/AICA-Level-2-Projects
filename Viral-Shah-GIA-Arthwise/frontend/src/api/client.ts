const API_BASE = '/api/v1';

export class ApiClient {
  private static token: string | null = localStorage.getItem('gia_arthwise_token');

  static setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('gia_arthwise_token', token);
    } else {
      localStorage.removeItem('gia_arthwise_token');
    }
  }

  static getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('gia_arthwise_token');
    }
    return this.token;
  }

  static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.setToken(null);
      // Optional callback/event
    }

    if (!response.ok) {
      let errorMsg = `API Error ${response.status}: ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) {
          errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch (_) {
        // fallback
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  static async uploadFile<T>(endpoint: string, formData: FormData): Promise<T> {
    const headers: Record<string, string> = {};
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }

    return response.json();
  }

  static getDownloadUrl(endpoint: string): string {
    const token = this.getToken();
    return `${API_BASE}${endpoint}?token=${token || ''}`;
  }
}
