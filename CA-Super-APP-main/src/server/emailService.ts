import nodemailer from 'nodemailer';
import dotenv from 'dotenv';

dotenv.config();

const AUTHORIZED_RESET_EMAIL = 'rishugarg006@gmail.com';
const OTP_EXPIRY_MS = 10 * 60 * 1000; // 10 minutes

interface OtpRecord {
  otp: string;
  role: 'ADMIN' | 'STAFF';
  expiresAt: number;
}

// In-memory store keyed by role ('ADMIN' | 'STAFF') so OTP never leaves the server
const otpStore = new Map<string, OtpRecord>();

export function isAuthorizedResetEmail(email?: string): boolean {
  const raw = (email || AUTHORIZED_RESET_EMAIL).toString().trim().toLowerCase();
  return raw === AUTHORIZED_RESET_EMAIL;
}

function generateSixDigitOtp(): string {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

function cleanEnvSecret(value?: string): string {
  if (!value) return '';
  const trimmed = value.trim().replace(/^['"]|['"]$/g, '').trim();
  if (!trimmed || trimmed.startsWith('MY_') || trimmed.toLowerCase().includes('your_')) {
    return '';
  }
  return trimmed;
}

export async function sendPasswordResetOtpEmail(
  emailInput?: string,
  roleInput?: string
): Promise<{ success: boolean; message: string; code?: string }> {
  dotenv.config();

  const email = (emailInput || AUTHORIZED_RESET_EMAIL).toString().trim().toLowerCase();
  if (!isAuthorizedResetEmail(email)) {
    return {
      success: false,
      code: 'UNAUTHORIZED_EMAIL',
      message: `Password reset is restricted strictly to registered email: ${AUTHORIZED_RESET_EMAIL}`
    };
  }

  const role: 'ADMIN' | 'STAFF' = (roleInput || 'ADMIN').toString().toUpperCase() === 'STAFF' ? 'STAFF' : 'ADMIN';
  const otp = generateSixDigitOtp();

  const subject = `CA Office Super App — ${role} Password Reset OTP`;
  const htmlBody = `
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; border: 1px solid #fde68a; border-radius: 12px; overflow: hidden;">
      <div style="background: linear-gradient(90deg, #b45309, #92400e); color: #ffffff; padding: 18px 24px;">
        <h2 style="margin: 0; font-size: 18px;">Rishu Garg &amp; Associates — CA Office Portal</h2>
        <p style="margin: 4px 0 0; font-size: 12px; color: #fde68a;">Password Reset Verification</p>
      </div>
      <div style="padding: 24px; background-color: #fffbeb; color: #451a03;">
        <p style="margin-top: 0; font-size: 14px;">Hello CA Rishu Garg,</p>
        <p style="font-size: 14px;">A password reset was requested for User ID: <strong>${role}</strong>.</p>
        <div style="background: #ffffff; border: 1px solid #fcd34d; border-radius: 10px; padding: 16px; text-align: center; margin: 20px 0;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #92400e; font-weight: bold;">Your 6-Digit Verification OTP</div>
          <div style="font-size: 32px; font-weight: 900; letter-spacing: 8px; color: #78350f; margin-top: 6px;">${otp}</div>
        </div>
        <p style="font-size: 12px; color: #78350f; margin-bottom: 0;">
          This OTP expires in 10 minutes. If you did not request this reset, please ignore this email.
        </p>
      </div>
    </div>
  `;
  const textBody = `Rishu Garg & Associates — CA Office Portal\n\nPassword reset verification OTP for User ID ${role}: ${otp}\n\nThis OTP expires in 10 minutes.`;

  const resendApiKey = cleanEnvSecret(process.env.RESEND_API_KEY);
  const smtpUser = cleanEnvSecret(process.env.SMTP_USER);
  const smtpPass = cleanEnvSecret(process.env.SMTP_PASS);
  let lastDeliveryError: string | null = null;

  // 1. Try Resend API if configured
  if (resendApiKey) {
    if (!resendApiKey.startsWith('re_')) {
      lastDeliveryError =
        'RESEND_API_KEY appears invalid (Resend keys start with "re_"). If you are using a Gmail App Password, put it in SMTP_PASS with SMTP_USER=rishugarg006@gmail.com instead.';
    } else {
      try {
        const fromAddress = cleanEnvSecret(process.env.SMTP_FROM) || 'CA Office Portal <onboarding@resend.dev>';
        const response = await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${resendApiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            from: fromAddress,
            to: [AUTHORIZED_RESET_EMAIL],
            subject,
            html: htmlBody,
            text: textBody
          })
        });

        if (response.ok) {
          otpStore.set(role, {
            otp,
            role,
            expiresAt: Date.now() + OTP_EXPIRY_MS
          });
          return {
            success: true,
            message: `Verification OTP has been sent to ${AUTHORIZED_RESET_EMAIL}. Please check your email inbox.`
          };
        }

        const errText = await response.text();
        let parsedMsg = errText;
        try {
          const parsed = JSON.parse(errText);
          parsedMsg = parsed?.message || errText;
        } catch {
          // keep raw text
        }

        if (response.status === 401 || parsedMsg.toLowerCase().includes('api key is invalid')) {
          lastDeliveryError =
            'Your RESEND_API_KEY secret is invalid or revoked. Please paste a valid Resend key (starts with "re_") in Settings > Secrets, or configure Gmail SMTP (SMTP_USER + SMTP_PASS), or click "Verify via Google Account" below.';
        } else {
          lastDeliveryError = `Email delivery via Resend failed: ${parsedMsg}`;
        }
        console.warn('Resend delivery status:', response.status, parsedMsg);
      } catch (err: any) {
        lastDeliveryError = err?.message || 'Error connecting to Resend email service.';
        console.warn('Resend request warning:', lastDeliveryError);
      }
    }
  }

  // 2. Try SMTP via Nodemailer if configured (also acts as fallback if Resend key is invalid)
  if (smtpUser && smtpPass) {
    try {
      const smtpHost = cleanEnvSecret(process.env.SMTP_HOST) || 'smtp.gmail.com';
      const smtpPort = Number(cleanEnvSecret(process.env.SMTP_PORT) || 465);
      const secure = process.env.SMTP_SECURE ? process.env.SMTP_SECURE === 'true' : smtpPort === 465;

      const transporter = nodemailer.createTransport({
        host: smtpHost,
        port: smtpPort,
        secure,
        auth: {
          user: smtpUser,
          pass: smtpPass.replace(/\s+/g, '')
        }
      });

      await transporter.sendMail({
        from: cleanEnvSecret(process.env.SMTP_FROM) || `"CA Office Portal" <${smtpUser}>`,
        to: AUTHORIZED_RESET_EMAIL,
        subject,
        text: textBody,
        html: htmlBody
      });

      otpStore.set(role, {
        otp,
        role,
        expiresAt: Date.now() + OTP_EXPIRY_MS
      });

      return {
        success: true,
        message: `Verification OTP has been sent to ${AUTHORIZED_RESET_EMAIL}. Please check your email inbox.`
      };
    } catch (err: any) {
      const smtpErr = err?.message || 'Check SMTP_USER and SMTP_PASS configuration.';
      console.warn('SMTP delivery warning:', smtpErr);
      lastDeliveryError = `Failed to send email via Gmail SMTP: ${smtpErr}. Make sure SMTP_PASS is a 16-character Google App Password (not your regular Gmail password).`;
    }
  }

  // 3. Delivery not possible — ensure no un-sent OTP remains stored
  otpStore.delete(role);
  if (lastDeliveryError) {
    return {
      success: false,
      code: 'EMAIL_DELIVERY_FAILED',
      message: lastDeliveryError
    };
  }

  return {
    success: false,
    code: 'EMAIL_NOT_CONFIGURED',
    message:
      'Email server is not configured (add SMTP_USER & SMTP_PASS or a valid RESEND_API_KEY in Settings > Secrets). You can verify instantly using "Verify via Google Account (rishugarg006@gmail.com)" below.'
  };
}

export function verifyPasswordResetOtp(
  roleInput?: string,
  otpInput?: string
): { success: boolean; message: string } {
  const role: 'ADMIN' | 'STAFF' = (roleInput || 'ADMIN').toString().toUpperCase() === 'STAFF' ? 'STAFF' : 'ADMIN';
  const cleanOtp = (otpInput || '').toString().trim();

  if (!cleanOtp || cleanOtp.length !== 6) {
    return {
      success: false,
      message: 'Please enter the valid 6-digit OTP received at rishugarg006@gmail.com.'
    };
  }

  const record = otpStore.get(role);
  if (!record) {
    return {
      success: false,
      message: 'No active OTP request found. Please request a new OTP to rishugarg006@gmail.com.'
    };
  }

  if (Date.now() > record.expiresAt) {
    otpStore.delete(role);
    return {
      success: false,
      message: 'OTP has expired. Please request a fresh OTP.'
    };
  }

  if (record.otp !== cleanOtp) {
    return {
      success: false,
      message: 'Invalid OTP. Please check the 6-digit code sent to rishugarg006@gmail.com.'
    };
  }

  otpStore.delete(role);
  return {
    success: true,
    message: 'OTP verified successfully.'
  };
}
