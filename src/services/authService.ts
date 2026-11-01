/**
 * DirhamTrack Security & Authentication Service
 * Communicates with backend endpoints for real Resend Email OTP delivery,
 * verification, and PIN reset sessions.
 */

export interface AuthStatusResponse {
  resendConfigured: boolean;
  fromEmail?: string;
}

export interface SendOtpResponse {
  success: boolean;
  message?: string;
  error?: string;
  resendId?: string;
  expiresAt?: number;
  retryAfter?: number;
  configured?: boolean;
}

export interface VerifyOtpResponse {
  success: boolean;
  message?: string;
  error?: string;
  resetToken?: string;
}

export interface ResetPinResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export class AuthService {
  /**
   * Check whether Resend API is configured on the backend server
   */
  static async getStatus(): Promise<AuthStatusResponse> {
    try {
      const res = await fetch('/api/auth/status');
      if (res.ok) {
        return await res.json();
      }
      return { resendConfigured: false };
    } catch (err) {
      console.warn('Failed to query auth status:', err);
      return { resendConfigured: false };
    }
  }

  /**
   * Request a real 6-digit OTP delivered via Resend Email API
   */
  static async sendOtp(email: string): Promise<SendOtpResponse> {
    try {
      const res = await fetch('/api/auth/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() })
      });

      const data = await res.json();
      if (!res.ok) {
        return {
          success: false,
          error: data.error || `HTTP error ${res.status}: Failed to send OTP`,
          retryAfter: data.retryAfter,
          configured: data.configured
        };
      }

      return data;
    } catch (err: any) {
      return {
        success: false,
        error: err.message || 'Network error connecting to email authentication service'
      };
    }
  }

  /**
   * Verify entered 6-digit OTP against backend store
   */
  static async verifyOtp(email: string, otp: string): Promise<VerifyOtpResponse> {
    try {
      const res = await fetch('/api/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim()
        })
      });

      const data = await res.json();
      if (!res.ok) {
        return {
          success: false,
          error: data.error || 'Verification failed. Please check the code.'
        };
      }

      return data;
    } catch (err: any) {
      return {
        success: false,
        error: err.message || 'Network error verifying code'
      };
    }
  }

  /**
   * Reset PIN on the backend using validated resetToken
   */
  static async resetPin(email: string, resetToken: string, newPin: string): Promise<ResetPinResponse> {
    try {
      const res = await fetch('/api/auth/reset-pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          resetToken,
          newPin: newPin.trim()
        })
      });

      const data = await res.json();
      if (!res.ok) {
        return {
          success: false,
          error: data.error || 'Failed to update PIN.'
        };
      }

      return data;
    } catch (err: any) {
      return {
        success: false,
        error: err.message || 'Network error saving new PIN'
      };
    }
  }
}
