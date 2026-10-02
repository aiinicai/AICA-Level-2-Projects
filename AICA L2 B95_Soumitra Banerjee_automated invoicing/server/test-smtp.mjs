// Standalone SMTP diagnostic - isolated from the app, the UI, and the Vite
// proxy, so whatever error comes out here is the real, underlying reason
// mail isn't sending. Run with: node server/test-smtp.mjs
import 'dotenv/config';
import nodemailer from 'nodemailer';

const host = process.env.SMTP_HOST;
const port = Number(process.env.SMTP_PORT) || 587;
const user = process.env.SMTP_USER;
const pass = process.env.SMTP_PASS;
const sender = process.env.SMTP_SENDER || user;

console.log('--- SMTP config being used ---');
console.log('SMTP_HOST:', host);
console.log('SMTP_PORT:', port);
console.log('SMTP_USER:', user);
console.log('SMTP_PASS length:', pass ? pass.length : 0, '(should be 16 if it is a Gmail App Password with no spaces)');
console.log('SMTP_SENDER:', sender);
console.log('DEMO_EMAIL_MODE:', process.env.DEMO_EMAIL_MODE);
console.log('-------------------------------\n');

if (!host || !user || !pass) {
  console.error('ERROR: SMTP_HOST, SMTP_USER or SMTP_PASS is missing/blank. Check .env is saved and this script is run from the project root.');
  process.exit(1);
}

const transporter = nodemailer.createTransport({
  host,
  port,
  secure: port === 465,
  auth: { user, pass },
});

try {
  console.log('Verifying SMTP connection/login...');
  await transporter.verify();
  console.log('✅ SMTP login succeeded.\n');

  console.log('Sending a real test email to yourself (' + user + ')...');
  const info = await transporter.sendMail({
    from: `"SMTP Test" <${sender}>`,
    to: user,
    subject: 'Quarterly Billing App - SMTP Test',
    text: 'If you are reading this, real SMTP sending is working correctly.',
  });
  console.log('✅ Email sent. messageId:', info.messageId);
  console.log('\nCheck the inbox/spam of', user, 'for this test email.');
} catch (err) {
  console.error('❌ FAILED. Full error details below:\n');
  console.error('message:', err.message);
  console.error('code:', err.code);
  console.error('responseCode:', err.responseCode);
  console.error('response:', err.response);
  process.exit(1);
}
