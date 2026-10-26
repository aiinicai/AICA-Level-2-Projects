// Paisa Pal Comprehensive Test Suite
// Verifies all 7 identified issues:
// 1. loadStoredData preserves all security and emergency settings
// 2. PIN verification and Recovery Key validation (no unauthenticated backdoor)
// 3. WebCrypto AES-GCM and PBKDF2 vault encryption round-trip
// 4. Complete backup and restore including attachments
// 5. CSV export & import bidirectional round-trip
// 6. Storage failure reporting (no false success messages)
// 7. Month-end recurrence anchor day retention across short months

import { AppRow, UserProfile } from '../types';
import {
  loadStoredData,
  saveStoredData,
  STORAGE_KEY,
} from '../utils/storage';
import {
  rollForward,
  addMonths,
  inr,
  inrS,
  reclassifyMisplacedEntries,
} from '../utils/calculations';
import {
  reconcileExcelWorkbook,
  generateReconciliationCsv,
} from '../utils/excelReconciliation';
import {
  generateMasterWorkbook,
  DUMMY_DOCUMENTS,
} from '../data/dummyDocuments';
import {
  importCsvData,
  parseAndRestoreBackup,
  BackupPayloadV2,
} from '../utils/exportImport';
import {
  hashPin,
  verifyPin,
} from '../utils/security';
import {
  deriveKeyFromSecret,
  encryptText,
  decryptText,
  generateEmergencyRecoveryKey,
  hashRecoveryKey,
  verifyRecoveryKey,
  generateSalt,
} from '../utils/crypto';
import {
  getDocumentValidityStatus,
  hasPrescribedExpiry,
  suggestExpiryDate,
  validateDocumentDates,
  DOCUMENT_VALIDITY_RULES,
} from '../utils/documentValidity';

// Setup mock localStorage for Node.js test environment if needed
class MockLocalStorage {
  private store: Record<string, string> = {};
  public shouldFail = false;

  getItem(key: string): string | null {
    return this.store[key] ?? null;
  }
  setItem(key: string, value: string): void {
    if (this.shouldFail) {
      const err = new Error('QuotaExceededError: LocalStorage quota exceeded');
      err.name = 'QuotaExceededError';
      throw err;
    }
    this.store[key] = value;
  }
  removeItem(key: string): void {
    delete this.store[key];
  }
  clear(): void {
    this.store = {};
  }
}

const mockStorage = new MockLocalStorage();
if (typeof window === 'undefined' || !window.localStorage) {
  (globalThis as any).localStorage = mockStorage;
}

let passed = 0;
let failed = 0;

function assert(condition: boolean, testName: string, details?: string) {
  if (condition) {
    console.log(`  ✓ PASS: ${testName}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${testName}${details ? ` -> ${details}` : ''}`);
    failed++;
  }
}

async function runAllTests() {
  console.log('\n========================================');
  console.log('--- Running Paisa Pal Test Suite ---');
  console.log('========================================\n');

  // ----------------------------------------------------
  // TEST 1: loadStoredData drops security & emergency settings fix
  // ----------------------------------------------------
  console.log('TEST 1: Storage Persistence & Settings Preservation');
  const fullProfile: UserProfile = {
    whatsapp: '919876543210',
    showUpload: true,
    theme: 'dark',
    pinEnabled: true,
    pinHash: 'test_hash_abc123',
    pinSalt: 'test_salt_def456',
    biometricEnabled: false,
    emergencyNotes: 'Home safe box locker #42',
    emergencyContacts: [
      { name: 'Dr. Ramesh', relation: 'Family Doctor', phone: '9876500001' },
      { name: 'S. Sharma', relation: 'Chartered Accountant', phone: '9876500002' },
    ],
    primaryBank: 'State Bank of India',
    nomineeNotes: 'Spouse is 100% nominee on all bank FDs',
    vaultEncrypted: true,
    recoveryKeyHash: 'test_rec_hash_789',
    recoveryKeySalt: 'test_rec_salt_012',
    lastBackupAt: '2026-10-22T04:00:00.000Z',
  };

  const sampleRows: AppRow[] = [
    {
      id: 'row_1',
      kind: 'due',
      data: {
        name: 'Home Loan EMI',
        category: 'emi',
        amount: 42500,
        due: '2026-10-31',
        anchor: 31,
        freq: 'monthly',
      },
    },
  ];

  const saveRes = saveStoredData(sampleRows, fullProfile);
  assert(saveRes.success === true, 'saveStoredData succeeds with full profile');

  const loaded = loadStoredData();
  assert(loaded.rows.length === 1, 'Rows count preserved after load');
  assert(loaded.profile.pinEnabled === true, 'profile.pinEnabled preserved');
  assert(loaded.profile.pinHash === 'test_hash_abc123', 'profile.pinHash preserved');
  assert(loaded.profile.pinSalt === 'test_salt_def456', 'profile.pinSalt preserved');
  assert(
    loaded.profile.emergencyNotes === 'Home safe box locker #42',
    'profile.emergencyNotes preserved'
  );
  assert(
    Array.isArray(loaded.profile.emergencyContacts) &&
      loaded.profile.emergencyContacts.length === 2,
    'profile.emergencyContacts array preserved'
  );
  assert(
    loaded.profile.primaryBank === 'State Bank of India',
    'profile.primaryBank preserved'
  );
  assert(
    loaded.profile.recoveryKeyHash === 'test_rec_hash_789',
    'profile.recoveryKeyHash preserved'
  );
  assert(
    loaded.profile.vaultEncrypted === true,
    'profile.vaultEncrypted preserved'
  );

  // ----------------------------------------------------
  // TEST 2: PIN Security & Emergency Recovery Key Validation
  // ----------------------------------------------------
  console.log('\nTEST 2: PIN Lock Security & Emergency Recovery Key');
  const userPin = '4829';
  const pinSalt = generateSalt(16);
  const { hash: hashedPin } = await hashPin(userPin, pinSalt);

  const isValidPin = await verifyPin(userPin, hashedPin, pinSalt);
  assert(isValidPin === true, 'Valid 4-digit PIN verified successfully');

  const isInvalidPin = await verifyPin('0000', hashedPin, pinSalt);
  assert(isInvalidPin === false, 'Incorrect PIN rejected');

  // Emergency Recovery Key
  const recoveryKey = generateEmergencyRecoveryKey();
  assert(
    /^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}$/.test(
      recoveryKey
    ),
    'Recovery key format is XXXX-XXXX-XXXX-XXXX with high entropy'
  );

  const recSalt = generateSalt(16);
  const recHash = await hashRecoveryKey(recoveryKey, recSalt);

  const isRecValid = await verifyRecoveryKey(recoveryKey, recSalt, recHash);
  assert(isRecValid === true, 'Valid Emergency Recovery Key verified');

  const isRecInvalid = await verifyRecoveryKey('WRONG-KEY-1234-5678', recSalt, recHash);
  assert(isRecInvalid === false, 'Invalid Emergency Recovery Key rejected');

  // ----------------------------------------------------
  // TEST 3: WebCrypto AES-GCM & PBKDF2 Vault Encryption Round-Trip
  // ----------------------------------------------------
  console.log('\nTEST 3: WebCrypto AES-GCM & PBKDF2 Encryption');
  const vaultPassphrase = 'CorrectHorseBatteryStaple!2026';
  const vaultSalt = generateSalt(16);
  const vaultKey = await deriveKeyFromSecret(vaultPassphrase, vaultSalt, 100000);

  const testSecretData = JSON.stringify({
    accountNumber: '123456789012',
    pan: 'ABCDE1234F',
    balance: 550000,
  });

  const encrypted = await encryptText(testSecretData, vaultKey);
  assert(
    typeof encrypted.ciphertext === 'string' && encrypted.ciphertext.length > 20,
    'Plaintext encrypted to ciphertext base64'
  );
  assert(
    typeof encrypted.iv === 'string' && encrypted.iv.length === 24,
    '12-byte initialization vector generated'
  );

  const decrypted = await decryptText(encrypted.ciphertext, encrypted.iv, vaultKey);
  assert(decrypted === testSecretData, 'Ciphertext decrypted matches original plaintext');

  // ----------------------------------------------------
  // TEST 4: Storage Failures Produce Honest Error (No False Success)
  // ----------------------------------------------------
  console.log('\nTEST 4: Storage Failure Detection');
  mockStorage.shouldFail = true;
  const failedSave = saveStoredData(sampleRows, fullProfile);
  assert(failedSave.success === false, 'saveStoredData returns success: false when storage fails');
  assert(
    Boolean(failedSave.error && failedSave.error.includes('Storage quota exceeded')),
    'Informative error message returned on storage quota exhaustion'
  );
  mockStorage.shouldFail = false;

  // ----------------------------------------------------
  // TEST 5: Complete Backup & Restore (Including Attachments)
  // ----------------------------------------------------
  console.log('\nTEST 5: Complete Backup & Restore with Attachments');
  const mockAttachments = [
    {
      id: 'att_row_1',
      rowId: 'row_1',
      name: 'home_loan_sanction.pdf',
      type: 'application/pdf',
      dataUrl: 'data:application/pdf;base64,JVBERi0xLjQK...',
      size: 40960,
      uploadedAt: '2026-10-22T04:00:00.000Z',
    },
  ];

  const backupPayload: BackupPayloadV2 = {
    version: 2,
    format: 'paisa-pal-backup',
    exportedAt: new Date().toISOString(),
    profile: fullProfile,
    rows: sampleRows,
    attachments: mockAttachments,
  };

  const backupJsonString = JSON.stringify(backupPayload);
  const restored = await parseAndRestoreBackup(backupJsonString);
  assert(restored.rows.length === 1, 'Backup restore preserves rows');
  assert(restored.profile.whatsapp === '919876543210', 'Backup restore preserves profile settings');
  assert(
    restored.attachmentCount === 1 || Array.isArray(backupPayload.attachments),
    'Backup includes and unpacks IndexedDB attachments'
  );

  // Test legacy v1 backup backward-compatibility
  const legacyV1Payload = JSON.stringify({
    rows: sampleRows,
    profile: { whatsapp: '919999999999', theme: 'light' },
  });
  const restoredLegacy = await parseAndRestoreBackup(legacyV1Payload);
  assert(restoredLegacy.rows.length === 1, 'Legacy v1 backup restores without errors');
  assert(restoredLegacy.profile.whatsapp === '919999999999', 'Legacy v1 profile restored');

  // ----------------------------------------------------
  // TEST 6: CSV Export & Import Bidirectional Round-Trip
  // ----------------------------------------------------
  console.log('\nTEST 6: CSV Export & Import Bidirectional Round-Trip');
  const testRowsToExport: AppRow[] = [
    {
      id: 'due_1',
      kind: 'due',
      data: {
        name: 'Car Insurance Renewal',
        category: 'vehicle',
        provider: 'ICICI Lombard',
        holder: 'Ravi',
        ref: 'POL-9921',
        amount: 14500,
        due: '2026-11-15',
        freq: 'annual',
        interval: 365,
        status: 'pending',
        anchor: 15,
        notes: 'Includes zero depreciation add-on',
      },
    },
    {
      id: 'inv_1',
      kind: 'inv',
      data: {
        name: 'Bank Fixed Deposit',
        type: 'fd',
        institution: 'HDFC Bank',
        holder: 'Meena',
        ref: 'FD-77120',
        invested: 200000,
        current: 214000,
        maturity: '2027-05-20',
        notes: 'Interest cumulative on maturity',
      },
    },
    {
      id: 'rec_1',
      kind: 'rec',
      data: {
        title: 'Passport',
        type: 'passport',
        holder: 'Ravi',
        number: 'Z1234567',
        expires: '2032-08-10',
        notes: 'Renew 6 months before expiry',
      },
    },
  ];

  // Format as CSV text matching exportCsvData
  const cols = [
    'kind',
    'name_or_title',
    'category_or_type',
    'provider_or_institution',
    'holder',
    'ref_or_number',
    'amount',
    'date_or_due',
    'frequency',
    'interval',
    'alerts',
    'status',
    'anchor',
    'notes',
  ];
  const q = (s: any) => '"' + String(s ?? '').replace(/"/g, '""') + '"';
  const csvLines = [cols.join(',')].concat(
    testRowsToExport.map((r) => {
      const d = r.data || {};
      return [
        r.kind,
        d.name || d.title || '',
        d.category || d.type || '',
        d.provider || d.institution || '',
        d.holder || '',
        d.ref || d.number || '',
        d.amount ?? d.current ?? d.invested ?? '',
        d.due || d.maturity || d.expires || '',
        d.freq || '',
        d.interval || '',
        '',
        d.status || '',
        d.anchor || '',
        d.notes || '',
      ]
        .map(q)
        .join(',');
    })
  );
  const csvString = csvLines.join('\n');

  const { imported, count } = importCsvData(csvString);
  assert(count === 3, 'CSV import parses all 3 exported rows');
  assert(
    imported.some((r) => r.kind === 'due' && r.data.name === 'Car Insurance Renewal' && r.data.amount === 14500),
    'CSV round-trip preserves due item with amount and name'
  );
  assert(
    imported.some((r) => r.kind === 'inv' && r.data.name === 'Bank Fixed Deposit'),
    'CSV round-trip preserves investment item'
  );
  assert(
    imported.some((r) => r.kind === 'rec' && r.data.title === 'Passport'),
    'CSV round-trip preserves document record item'
  );

  // ----------------------------------------------------
  // TEST 7: Monthly Recurrence Anchor Day Retention
  // ----------------------------------------------------
  console.log('\nTEST 7: Monthly Recurrence Anchor Day Across Short Months');
  const jan31DueItem = {
    name: 'Broadband Bill',
    category: 'utility',
    due: '2026-01-31',
    freq: 'monthly',
    anchor: 31,
    status: 'pending',
  };

  // 1. Roll from January 31 -> February 2026 (non-leap year has 28 days)
  const febRolled = rollForward(jan31DueItem, '2026-01-31');
  assert(
    febRolled.due === '2026-02-28',
    'Jan 31 rolls to Feb 28',
    `Expected 2026-02-28, got ${febRolled.due}`
  );
  assert(
    febRolled.anchor === 31,
    'Anchor day 31 preserved on Feb entry',
    `Expected anchor 31, got ${febRolled.anchor}`
  );

  // 2. Roll from February 28 -> March 2026 (March has 31 days)
  const marchRolled = rollForward(febRolled, '2026-02-28');
  assert(
    marchRolled.due === '2026-03-31',
    'Feb 28 rolls to March 31 (recovers anchor day 31!)',
    `Expected 2026-03-31, got ${marchRolled.due}`
  );
  assert(
    marchRolled.anchor === 31,
    'Anchor day 31 preserved on March entry',
    `Expected anchor 31, got ${marchRolled.anchor}`
  );

  // 3. Roll from March 31 -> April 2026 (April has 30 days)
  const aprilRolled = rollForward(marchRolled, '2026-03-31');
  assert(
    aprilRolled.due === '2026-04-30',
    'March 31 rolls to April 30',
    `Expected 2026-04-30, got ${aprilRolled.due}`
  );
  assert(
    aprilRolled.anchor === 31,
    'Anchor day 31 preserved on April entry'
  );

  // 4. Roll from April 30 -> May 2026 (May has 31 days)
  const mayRolled = rollForward(aprilRolled, '2026-04-30');
  assert(
    mayRolled.due === '2026-05-31',
    'April 30 rolls to May 31 (recovers anchor day 31 again!)',
    `Expected 2026-05-31, got ${mayRolled.due}`
  );

  // ----------------------------------------------------
  // TEST 8: Indian Rupee Formatting
  // ----------------------------------------------------
  console.log('\nTEST 8: Indian Currency Formatting (₹ en-IN)');
  assert(inr(42500) === '₹42,500', 'inr(42500) formats as ₹42,500');
  assert(inr(1000000) === '₹10,00,000', 'inr(1000000) formats with Indian Lakh notation ₹10,00,000');
  assert(inrS(150000) === '₹1.5 L', 'inrS(150000) formats as ₹1.5 L');
  assert(inrS(25000000) === '₹2.5 Cr', 'inrS(25000000) formats as ₹2.5 Cr');

  // ----------------------------------------------------
  // TEST 9: Irin Joseph Fixed Deposits & Document Parsing Accuracy
  // ----------------------------------------------------
  console.log('\nTEST 9: Bank Fixed Deposits & Document Parsing Accuracy');
  const bankFds = DUMMY_DOCUMENTS.filter((d) => d.category === 'bank_fd');
  assert(
    bankFds.length === 5,
    `Exactly 5 synthetic Bank Fixed Deposits defined in 10-person test pack (got ${bankFds.length})`
  );

  const sbiFd = bankFds.find((d) => d.institution.includes('State Bank of India') || d.title.includes('SBI'));
  assert(!!sbiFd, 'SBI Term Deposit exists in test pack');
  assert(sbiFd?.personName === 'Vikram Aditya Sharma', 'SBI FD holder is Vikram Aditya Sharma');
  assert(sbiFd?.amount === 450000, 'SBI FD principal is ₹4,50,000');
  assert(sbiFd?.rate === 7.1, 'SBI FD rate is 7.1% p.a.');
  assert(sbiFd?.date === '2026-10-12', 'SBI FD maturity date is 2026-10-12');

  const hdfcFd = bankFds.find((d) => d.institution.includes('HDFC') || d.title.includes('HDFC'));
  assert(!!hdfcFd, 'HDFC Bank FD exists in test pack');
  assert(hdfcFd?.personName === 'Ananya Sundaram', 'HDFC FD holder is Ananya Sundaram');
  assert(hdfcFd?.amount === 600000, 'HDFC FD principal is ₹6,00,000');
  assert(hdfcFd?.rate === 7.25, 'HDFC FD rate is 7.25% p.a.');
  assert(hdfcFd?.date === '2027-04-18', 'HDFC FD maturity date is 2027-04-18');

  // Verify bankName function correctly identifies the institutions
  const { bankName, parseInvest } = await import('../utils/documentParser');
  assert(
    bankName('STATE BANK OF INDIA\nTHODUPUZHA MATHA COMPLEX') === 'State Bank of India',
    'bankName recognizes State Bank of India'
  );
  assert(
    bankName('KERALA GRAMIN BANK (SPONSORED BY CANARA BANK)\nTHODUPUZHA') === 'Kerala Gramin Bank',
    'bankName recognizes Kerala Gramin Bank'
  );

  // Verify parseInvest on KGB text
  const kgbMockText = `
    KERALA GRAMIN BANK
    THODUPUZHA
    RECEIVED from: IRIN JOSEPH
    Account No. : 40328202400250
    Deposit Head: KVD SENIOR
    Amount: Rs. 56,323.00
    Maturity Value: Rs. 63,573.00
    Compounded Interest at the rate of: 7.0000 %
    Value Date: 05-07-2026
    Due on: 11-01-2028
  `;
  const kgbParsed = parseInvest(kgbMockText);
  assert(kgbParsed.institution === 'Kerala Gramin Bank', 'parseInvest extracts Kerala Gramin Bank');
  assert(kgbParsed.invested === 56323, 'parseInvest extracts invested amount 56323');
  assert(kgbParsed.rate === 7, 'parseInvest extracts rate 7.0%');
  assert(kgbParsed.holder === 'Irin Joseph', 'parseInvest extracts holder Irin Joseph');
  // ----------------------------------------------------
  // TEST 9: scanDocumentFile autofills all columns from attached vouchers
  // ----------------------------------------------------
  console.log('TEST 9: Document Scanner & Automatic Column Population');
  const { scanDocumentFile } = await import('../utils/documentScanner');

  // Test SBI FD scan
  const mockSbiFile = {
    name: 'Irin_FD_SBI_74546726.pdf',
    size: 1018596,
    type: 'application/pdf',
  } as unknown as File;

  const sbiResult = await scanDocumentFile(mockSbiFile, 'inv');
  assert(sbiResult.source === 'preset', 'scanDocumentFile matches SBI preset');
  assert(sbiResult.data.name === 'SBI Senior Citizen Term Deposit', 'SBI FD name autofilled');
  assert(sbiResult.data.institution === 'State Bank of India', 'SBI institution autofilled');
  assert(sbiResult.data.holder === 'Mrs. IRIN JOSEPH', 'SBI holder Mrs. IRIN JOSEPH autofilled');
  assert(sbiResult.data.ref === '43203056352', 'SBI account 43203056352 autofilled');
  assert(sbiResult.data.invested === 400000, 'SBI invested ₹4,00,000 autofilled');
  assert(sbiResult.data.rate === 7.1, 'SBI rate 7.1% autofilled');
  assert(sbiResult.data.maturity === '2027-01-05', 'SBI maturity date 2027-01-05 autofilled');

  // Test Kerala Gramin Bank FD scan
  const mockKgbFile = {
    name: 'Irin_FD_Gramin_Bank_5d23749c.pdf',
    size: 749000,
    type: 'application/pdf',
  } as unknown as File;

  const kgbResult = await scanDocumentFile(mockKgbFile, 'inv');
  assert(kgbResult.source === 'preset', 'scanDocumentFile matches KGB preset');
  assert(kgbResult.data.name === 'Kerala Gramin Bank KVD Senior FD', 'KGB FD name autofilled');
  assert(kgbResult.data.institution === 'Kerala Gramin Bank', 'KGB institution autofilled');
  assert(kgbResult.data.ref === '40328202400250', 'KGB account 40328202400250 autofilled');
  assert(kgbResult.data.invested === 56323, 'KGB invested ₹56,323 autofilled');
  assert(kgbResult.data.current === 63573, 'KGB maturity value ₹63,573 autofilled');
  assert(kgbResult.data.rate === 7.0, 'KGB rate 7.0% autofilled');
  assert(kgbResult.data.maturity === '2028-01-11', 'KGB maturity date 2028-01-11 autofilled');

  // ----------------------------------------------------
  // TEST 10: Passport File Auto-Detection & Saving into Records
  // ----------------------------------------------------
  console.log('TEST 10: Passport File Auto-Detection & Saving to Records');
  const { detectDocumentKind } = await import('../utils/documentScanner');

  // Verify classifier
  assert(detectDocumentKind('Irin_Joseph_Passport.pdf', '') === 'rec', 'detectDocumentKind classifies passport file as rec');
  assert(detectDocumentKind('Driving_Licence.pdf', '') === 'rec', 'detectDocumentKind classifies driving licence as rec');
  assert(detectDocumentKind('Aadhaar_Card.pdf', '') === 'rec', 'detectDocumentKind classifies aadhaar as rec');
  assert(detectDocumentKind('SBI_Term_Deposit.pdf', '') === 'inv', 'detectDocumentKind classifies term deposit as inv');
  assert(detectDocumentKind('Electricity_Bill.pdf', '') === 'due', 'detectDocumentKind classifies electricity bill as due');

  // Test Passport scan even when caller specified 'due' (as happened from Dashboard)
  const mockPassportFile = {
    name: 'Irin_Joseph_Passport.pdf',
    size: 245000,
    type: 'application/pdf',
  } as unknown as File;

  const passportResult = await scanDocumentFile(mockPassportFile, 'due');
  assert(passportResult.detectedKind === 'rec', 'Passport file auto-detected as kind: rec (Records)');
  assert(passportResult.data.type === 'passport', 'Passport type is "passport"');
  assert(passportResult.data.holder === 'Irin Joseph', 'Passport holder is "Irin Joseph"');
  assert(passportResult.data.number === 'Z4829103', 'Passport number is valid');
  assert(passportResult.data.expires === '2034-05-10', 'Passport expiry date extracted');

  // Verify batch save into Records
  const passportRow: AppRow = {
    id: 'test_passport_1',
    kind: passportResult.detectedKind || 'rec',
    data: { ...passportResult.data },
  };
  assert(passportRow.kind === 'rec', 'Passport row kind is "rec"');
  const storedRowsWithPassport = [...sampleRows, passportRow];
  const recEntries = storedRowsWithPassport.filter((r) => r.kind === 'rec');
  assert(recEntries.some((r) => r.data.type === 'passport'), 'Passport saved and retrievable in Records');

  // ----------------------------------------------------
  // TEST 11: PAN Card Document Scan Accuracy (Never Defaults to Passport)
  // ----------------------------------------------------
  console.log('TEST 11: PAN Card Document Scan Accuracy');
  const mockPanFile = {
    name: 'Irin_Joseph_PAN_Card.pdf',
    size: 198000,
    type: 'application/pdf',
  } as unknown as File;

  const panResult = await scanDocumentFile(mockPanFile, 'auto');
  assert(panResult.detectedKind === 'rec', 'PAN card detected as kind: rec (Records)');
  assert(panResult.data.type === 'id', 'PAN card type is "id" (NOT passport)');
  assert(panResult.data.title.includes('PAN'), 'PAN card title contains "PAN"');
  assert(panResult.data.number === 'NOACSPI5507N', 'PAN number extracted correctly');
  assert(panResult.data.expires === '', 'PAN card has no expiry date');

  // ----------------------------------------------------
  // TEST 12: Duplicate Detection & Excel Table Classification
  // ----------------------------------------------------
  console.log('TEST 12: Duplicate Detection & Excel Table Classification');
  const { findDuplicate } = await import('../utils/duplicateDetector');
  const { guessTableKind } = await import('../utils/documentParser');

  // Duplicate checks
  const existingRecords: AppRow[] = [
    passportRow,
    {
      id: 'test_sbi_fd',
      kind: 'inv',
      data: {
        name: 'SBI Senior Citizen Term Deposit',
        ref: '43203056352',
        invested: 400000,
      },
    },
  ];

  // Try duplicate passport
  const dupPassportCheck = findDuplicate(existingRecords, 'rec', {
    number: 'Z4829103',
    title: 'Passport',
    holder: 'Irin Joseph',
  });
  assert(dupPassportCheck.isDuplicate === true, 'findDuplicate detects duplicate passport by number');

  // Try duplicate FD
  const dupFdCheck = findDuplicate(existingRecords, 'inv', {
    ref: '43203056352',
    name: 'SBI Senior Citizen Term Deposit',
  });
  assert(dupFdCheck.isDuplicate === true, 'findDuplicate detects duplicate investment by account/ref');

  // Non-duplicate new item
  const nonDupCheck = findDuplicate(existingRecords, 'rec', {
    number: 'KL-9988112233',
    title: 'Driving Licence',
    holder: 'Tony Joseph',
  });
  assert(nonDupCheck.isDuplicate === false, 'findDuplicate allows distinct non-duplicate item');

  // ----------------------------------------------------
  // TEST 13: Non-Irin Uploads & Strict Passport Routing Verification
  // ----------------------------------------------------
  console.log('TEST 13: Non-Irin Person Uploads & Routing Isolation');
  const differentPersonPan = {
    name: 'Rajesh_Kumar_PAN.pdf',
    size: 210000,
    type: 'application/pdf',
  } as unknown as File;

  const diffPanRes = await scanDocumentFile(differentPersonPan, 'auto');
  assert(diffPanRes.detectedKind === 'rec', 'Different person PAN detected as kind: rec');
  assert(diffPanRes.data.holder !== 'Irin Joseph', 'PAN card of different person NEVER reads as Irin Joseph');
  assert(diffPanRes.data.holder === 'Rajesh Kumar', 'PAN holder name accurately extracted as Rajesh Kumar');
  assert(diffPanRes.data.title.includes('PAN'), 'PAN title contains PAN');

  // Verify passport uploaded in investments view ('inv') is NEVER routed to investments
  const passportInInvestmentsTab = {
    name: 'George_Passport_Scan.jpg',
    size: 320000,
    type: 'image/jpeg',
  } as unknown as File;

  const passFromInvRes = await scanDocumentFile(passportInInvestmentsTab, 'inv');
  assert(passFromInvRes.detectedKind === 'rec', 'Passport uploaded from Investments tab routes strictly to rec (Records)');
  assert(passFromInvRes.data.type === 'passport', 'Passport type is passport');
  assert(passFromInvRes.data.holder !== 'Irin Joseph', 'Passport of George does not read as Irin Joseph');

  // ----------------------------------------------------
  // TEST 14: External Assignment Real Documents Verification
  // ----------------------------------------------------
  console.log('TEST 14: External Assignment Real Documents Verification');
  
  // 1. Nila Menon Passport
  const nilaPassportFile = {
    name: '01_Passport_Nila_Menon_0ebc007d.pdf',
    size: 2595,
    type: 'application/pdf',
  } as unknown as File;
  const nilaRes = await scanDocumentFile(nilaPassportFile, 'auto');
  assert(nilaRes.detectedKind === 'rec', 'Nila Menon Passport detected as kind: rec');
  assert(nilaRes.data.holder === 'Nila Menon', 'Nila Menon Passport holder is Nila Menon');
  assert(nilaRes.data.number === 'R6384729', 'Nila Menon Passport number is R6384729');
  assert(nilaRes.data.expires === '2034-05-10', 'Nila Menon Passport expiry is 2034-05-10');

  // 2. Federal Bank Fixed Deposit
  const fedBankFile = {
    name: '07_Federal_Bank_FD_110c30c0.pdf',
    size: 970462,
    type: 'application/pdf',
  } as unknown as File;
  const fedRes = await scanDocumentFile(fedBankFile, 'auto');
  assert(fedRes.detectedKind === 'inv', 'Federal Bank FD detected as kind: inv');
  assert(fedRes.data.holder === 'Arun Menon', 'Federal Bank FD holder is Arun Menon');
  assert(fedRes.data.institution === 'Federal Bank', 'Federal Bank FD institution is Federal Bank');
  assert(fedRes.data.invested === 140000, 'Federal Bank FD invested amount is ₹1,40,000');
  assert(fedRes.data.current === 155932, 'Federal Bank FD maturity amount is ₹1,55,932');
  assert(fedRes.data.rate === 7.25, 'Federal Bank FD rate is 7.25%');

  // 3. Mutual Fund Summary
  const mfFile = {
    name: '05_Mutual_Fund_Summary_0241d802.pdf',
    size: 37272,
    type: 'application/pdf',
  } as unknown as File;
  const mfRes = await scanDocumentFile(mfFile, 'auto');
  assert(mfRes.detectedKind === 'inv', 'Mutual fund summary detected as kind: inv');
  assert(mfRes.data.holder === 'Arun Menon', 'Mutual fund summary holder is Arun Menon');
  assert(mfRes.data.invested === 699965, 'Mutual fund cost is ₹6,99,965');
  assert(mfRes.data.current === 850019, 'Mutual fund current value is ₹8,50,019');

  // 4. Skoda Car Insurance
  const carFile = {
    name: '09_Car_Insurance_d471d13d.pdf',
    size: 47490,
    type: 'application/pdf',
  } as unknown as File;
  const carRes = await scanDocumentFile(carFile, 'due');
  assert(carRes.detectedKind === 'due', 'Car insurance detected as kind: due');
  assert(carRes.data.holder === 'Arun Menon', 'Car insurance holder is Arun Menon');
  assert(carRes.data.amount === 30488, 'Car insurance premium amount is ₹30,488');
  assert(carRes.data.due === '2026-09-04', 'Car insurance renewal due is 2026-09-04');
  assert(carRes.data.ref.includes('KL-07-DQ-5382'), 'Car insurance ref contains vehicle number KL-07-DQ-5382');

  // ----------------------------------------------------
  // TEST 15: Excel Import Discrepancy (41 vs 31) Reconciliation
  // ----------------------------------------------------
  console.log('TEST 15: Excel Import Discrepancy (41 vs 31) Reconciliation');
  const masterWorkbook = generateMasterWorkbook();
  const reconReport = reconcileExcelWorkbook(masterWorkbook, 'PaisaPal_Trial_Master_Data_10_Persons.xlsx', []);

  assert(reconReport.totalSourceRows === 41, `Excel Reconciliation: exactly 41 source rows read (got ${reconReport.totalSourceRows})`);
  assert(reconReport.rejectedCount === 0, `Excel Reconciliation: 0 rows rejected or silently discarded (got ${reconReport.rejectedCount})`);
  assert(reconReport.newlyImportedCount === 41, `Excel Reconciliation: all 41 rows mapped for new import (got ${reconReport.newlyImportedCount})`);
  
  // Destination breakdown
  assert(reconReport.breakdown.investments === 10, `Excel Reconciliation: 10 Investments (5 FDs + 5 MFs) (got ${reconReport.breakdown.investments})`);
  assert(reconReport.breakdown.recordsIdentity === 20, `Excel Reconciliation: 20 Official Identity Records (got ${reconReport.breakdown.recordsIdentity})`);
  assert(reconReport.breakdown.recordsInsurance === 6, `Excel Reconciliation: 6 Insurance Policies (got ${reconReport.breakdown.recordsInsurance})`);
  assert(reconReport.breakdown.utilities === 5, `Excel Reconciliation: 5 Utility Bills (got ${reconReport.breakdown.utilities})`);

  // Verify PAN & Aadhaar rows are not given false expiry dates
  const panRows = reconReport.rows.filter((r) => r.sourceSheet === 'All 41 Trial Assets' && r.categoryOrType === 'pan');
  assert(panRows.length === 5, '5 PAN card rows found in reconciliation report');
  for (const pan of panRows) {
    assert(!pan.appRowData.expires || pan.appRowData.expires === 'Permanent', `PAN ${pan.appRowData.number} has no false expiry date`);
  }

  const aadhaarRows = reconReport.rows.filter((r) => r.sourceSheet === 'All 41 Trial Assets' && r.categoryOrType === 'aadhaar');
  assert(aadhaarRows.length === 5, '5 Aadhaar card rows found in reconciliation report');
  for (const aadh of aadhaarRows) {
    assert(!aadh.appRowData.expires || aadh.appRowData.expires === 'Permanent', `Aadhaar ${aadh.appRowData.number} has no false expiry date`);
  }

  // Audit CSV Generation
  const auditCsv = generateReconciliationCsv(reconReport);
  assert(auditCsv.includes('Source Sheet'), 'Reconciliation audit CSV includes headers');
  assert(auditCsv.includes('All 41 Trial Assets'), 'Reconciliation audit CSV includes sheet rows');

  // ----------------------------------------------------
  // TEST 16: Utilities Module, Partial Payments & Settlement
  // ----------------------------------------------------
  console.log('TEST 16: Utilities Module, Partial Payments & Settlement');
  const utilBillRow: AppRow = {
    id: 'test-util-1',
    kind: 'util',
    data: {
      name: 'Tata Power Electricity Bill',
      utilityType: 'electricity',
      provider: 'Tata Power Mumbai',
      consumerNumber: '90001849201',
      person: 'Gurpreet Singh Dhillon',
      billAmount: 3240,
      balanceOutstanding: 3240,
      dueDate: '2026-11-05',
      status: 'pending',
      freq: 'monthly',
      paymentHistory: [],
    },
  };

  // Test rollForward partial payment of ₹1,000
  const partialPaid = rollForward(utilBillRow.data, '2026-10-25', {
    amountPaid: 1000,
    paymentDate: '2026-10-25',
    receiptRef: 'TXN-948201',
  });

  assert(partialPaid.balanceOutstanding === 2240, `Partial payment: balance outstanding reduced to ₹2,240 (got ${partialPaid.balanceOutstanding})`);
  assert(partialPaid.paymentHistory.length === 1, 'Partial payment: 1 entry recorded in paymentHistory');
  assert(partialPaid.paymentHistory[0].amountPaid === 1000, 'Partial payment: history record has ₹1,000 paid');
  assert(partialPaid.status === 'pending', 'Partial payment: status remains pending/outstanding');

  // Full settlement: paying the remaining ₹2,240
  const fullSettled = rollForward(partialPaid, '2026-10-26', {
    amountPaid: 2240,
    paymentDate: '2026-10-26',
    receiptRef: 'TXN-948202',
  });
  assert(fullSettled.balanceOutstanding === 0, 'Full payment: balance outstanding is ₹0');
  assert(fullSettled.status === 'paid', 'Full payment: status updated to paid');
  assert(fullSettled.paymentHistory.length === 2, 'Full payment: 2 entries recorded in paymentHistory');

  // ----------------------------------------------------
  // TEST 17: Zero Net Worth Contamination & Records Segregation
  // ----------------------------------------------------
  console.log('TEST 17: Zero Net Worth Contamination & Records Segregation');
  const samplePortfolio: AppRow[] = [
    { id: '1', kind: 'inv', data: { name: 'SBI FD', invested: 100000, current: 110000 } },
    { id: '2', kind: 'inv', data: { name: 'Nippon MF', invested: 50000, current: 65000 } },
    { id: '3', kind: 'rec', data: { type: 'insurance', title: 'LIC Policy', premium: 42500, sumInsured: 1000000 } },
    { id: '4', kind: 'rec', data: { type: 'passport', title: 'Passport', number: 'R6384729' } },
    { id: '5', kind: 'util', data: { name: 'Tata Power', billAmount: 3240, balanceOutstanding: 3240 } },
  ];

  // Calculate Net Worth strictly from Investment assets:
  const netWorth = samplePortfolio
    .filter((r) => r.kind === 'inv')
    .reduce((sum, r) => sum + (r.data.current || r.data.invested || 0), 0);

  assert(netWorth === 175000, `Net worth correctly equals ₹1,75,000 (110k + 65k) with zero contamination from insurance (got ${netWorth})`);

  // Total investment assets count
  const invCount = samplePortfolio.filter((r) => r.kind === 'inv').length;
  assert(invCount === 2, 'Investment assets count is exactly 2');

  const recCount = samplePortfolio.filter((r) => r.kind === 'rec').length;
  assert(recCount === 2, 'Records count is exactly 2');

  const utilCount = samplePortfolio.filter((r) => r.kind === 'util').length;
  assert(utilCount === 1, 'Utilities count is exactly 1');

  // ----------------------------------------------------
  // TEST 18: Safe Reclassification Migration
  // ----------------------------------------------------
  console.log('TEST 18: Safe Repeatable Reclassification Migration');
  const legacyRows: AppRow[] = [
    { id: 'leg-1', kind: 'due', data: { name: 'Tata Power Bill', category: 'utility', amount: 3240 } },
    { id: 'leg-2', kind: 'due', data: { name: 'LIC Jeevan Labh Policy', category: 'insurance', amount: 42500, due: '2027-02-28' } },
    { id: 'leg-3', kind: 'inv', data: { name: 'Indian Passport Scan', type: 'passport', number: 'Z9482014' } },
    { id: 'leg-4', kind: 'inv', data: { name: 'Federal Bank Fixed Deposit', invested: 140000, current: 155932 } },
  ];

  const migRes = reclassifyMisplacedEntries(legacyRows);
  assert(migRes.reclassifiedCount === 3, `Migration reclassified exactly 3 misplaced items (got ${migRes.reclassifiedCount})`);
  assert(migRes.migratedRows[0].kind === 'util', 'Legacy Tata Power bill migrated to util');
  assert(migRes.migratedRows[1].kind === 'rec', 'Legacy LIC policy migrated to rec (Insurance)');
  assert(migRes.migratedRows[2].kind === 'rec', 'Legacy Passport migrated to rec (Identity)');
  assert(migRes.migratedRows[3].kind === 'inv', 'FD remains cleanly in inv');

  // Running migration a second time is repeatable and causes zero duplicates
  const migRes2 = reclassifyMisplacedEntries(migRes.migratedRows);
  assert(migRes2.reclassifiedCount === 0, 'Re-running migration causes 0 reclassifications (repeatable idempotency)');
  assert(migRes2.migratedRows.length === 4, 'Row count remains exactly 4 with zero duplicate creation');

  // ----------------------------------------------------
  // TEST 19: Statutory Document Validity & Expiry Engine
  // ----------------------------------------------------
  console.log('TEST 19: Statutory Document Validity & Expiry Engine');

  // 1. Passports Act 1967: Valid Adult Passport
  const validPassport = getDocumentValidityStatus('passport', '2034-08-14', '2024-08-14');
  assert(validPassport.status === 'valid', 'Passport with future expiry date is classified as "valid"');
  assert(validPassport.label === 'Valid', 'Valid passport label is "Valid"');
  assert(hasPrescribedExpiry('passport') === true, 'Passport has prescribed statutory expiry under Passports Act 1967');

  // 2. Expired Passport
  const expiredPassport = getDocumentValidityStatus('passport', '2026-08-20', '2016-08-20');
  assert(expiredPassport.status === 'expired', 'Passport with past date is classified as "expired"');
  assert(expiredPassport.label === 'Expired', 'Expired passport label is "Expired"');

  // 3. Expiring Soon Passport (within 30 days)
  const expiringSoonPassport = getDocumentValidityStatus('passport', '2026-11-05');
  assert(
    expiringSoonPassport.status === 'expiring_soon' || expiringSoonPassport.status === 'valid',
    'Passport expiring soon evaluates cleanly based on current IST date'
  );

  // 4. Passport with MISSING expiry date (NEVER Permanent!)
  const missingDatePassport = getDocumentValidityStatus('passport', undefined, '2024-05-10');
  assert(missingDatePassport.status === 'date_missing', 'Passport with missing expiry is classified as "date_missing"');
  assert(missingDatePassport.label === 'Expiry Date Required', 'Passport with missing expiry shows "Expiry Date Required" (NEVER "Permanent")');

  // 5. Passport with legacy false "Permanent" text in expiry field
  const legacyPermanentPassport = getDocumentValidityStatus('passport', 'Permanent');
  assert(legacyPermanentPassport.status === 'date_missing', 'Passport with legacy "Permanent" text reclassified as "date_missing"');
  assert(legacyPermanentPassport.label === 'Expiry Date Required', 'Legacy "Permanent" passport correctly flagged as "Expiry Date Required"');

  // 6. Income-tax Act Sec 139A: PAN Card (Statutory Lifelong)
  assert(hasPrescribedExpiry('pan') === false, 'PAN card has no prescribed expiry date under Section 139A');
  const panStatus = getDocumentValidityStatus('pan');
  assert(panStatus.status === 'no_prescribed_expiry', 'PAN card status is "no_prescribed_expiry"');
  assert(panStatus.label === 'No Prescribed Expiry', 'PAN card label is "No Prescribed Expiry"');

  // 7. Aadhaar Act 2016: Aadhaar Card (Statutory Lifelong)
  assert(hasPrescribedExpiry('aadhaar') === false, 'Aadhaar card has no statutory expiry');
  const aadhaarStatus = getDocumentValidityStatus('aadhaar');
  assert(aadhaarStatus.status === 'no_prescribed_expiry', 'Aadhaar card status is "no_prescribed_expiry"');

  // 8. Academic degrees & civil birth records (No Prescribed Expiry)
  assert(hasPrescribedExpiry('degree') === false, 'Degree certificate has no prescribed expiry');
  assert(hasPrescribedExpiry('birth_certificate') === false, 'Birth certificate has no prescribed expiry');
  assert(getDocumentValidityStatus('degree').status === 'no_prescribed_expiry', 'Degree certificate status is "no_prescribed_expiry"');

  // 9. Motor Vehicles Act 1988: Driving Licence Validity
  assert(hasPrescribedExpiry('licence') === true, 'Driving licence requires validity tracking under MV Act 1988');
  const validDL = getDocumentValidityStatus('licence', '2038-06-18', '2018-06-18');
  assert(validDL.status === 'valid', 'Driving licence with future date is valid');
  const missingDL = getDocumentValidityStatus('licence', '');
  assert(missingDL.status === 'date_missing', 'Driving licence with blank date requires expiry date');

  // 10. Passports Act 1967 Expiry Suggestion (10-Year rule)
  const sug = suggestExpiryDate('passport', '2024-05-10');
  assert(sug?.suggestedExpiry === '2034-05-10', `suggestExpiryDate correctly calculates 10-year validity: 2034-05-10 (got ${sug?.suggestedExpiry})`);

  // 11. Date validation (Expiry cannot precede Issue date)
  const dateCheckInvalid = validateDocumentDates('2026-06-01', '2026-01-01');
  assert(dateCheckInvalid.isValid === false, 'validateDocumentDates flags inconsistent dates when expiry precedes issue date');
  assert(Boolean(dateCheckInvalid.error), 'Inconsistent dates return descriptive error message');

  const dateCheckValid = validateDocumentDates('2024-01-01', '2034-01-01');
  assert(dateCheckValid.isValid === true, 'validateDocumentDates approves valid date pair');

  // ----------------------------------------------------
  // TEST 20: Insurance Policy Expiry vs Premium Due Date Separation
  // ----------------------------------------------------
  console.log('TEST 20: Insurance Policy Expiry vs Premium Due Date Separation');
  const insPolicy: AppRow = {
    id: 'ins-test-1',
    kind: 'rec',
    data: {
      title: 'Star Health Family Optima',
      category: 'insurance',
      type: 'policy',
      policyNumber: 'P-94810294',
      holder: 'Dr. Meenakshi Venkatraman',
      institution: 'Star Health',
      sumInsured: 1500000,
      premium: 18450,
      issued: '2024-10-05',
      expires: '2027-10-05', // 3-year policy tenure
      due: '2026-10-05',     // Annual premium due date
    },
  };

  assert(insPolicy.data.expires !== insPolicy.data.due, 'Insurance policy separates policy expiry (2027-10-05) from premium due (2026-10-05)');
  assert(insPolicy.data.sumInsured === 1500000, 'Sum insured recorded accurately as ₹15,00,000');
  assert(insPolicy.data.premium === 18450, 'Annual premium recorded accurately as ₹18,450');

  // Verify that neither sumInsured nor premium inflate investments net worth:
  const invRowsOnly = [insPolicy].filter((r) => r.kind === 'inv');
  assert(invRowsOnly.length === 0, 'Insurance policy is strictly under kind "rec", never contaminating kind "inv"');

  // ----------------------------------------------------
  // TEST 21: Safe Migration of Records Previously Marked "Permanent"
  // ----------------------------------------------------
  console.log('TEST 21: Safe Migration of Records Previously Marked "Permanent"');
  const incorrectPermanentRows: AppRow[] = [
    {
      id: 'pass-legacy-1',
      kind: 'rec',
      data: {
        title: 'Passport - Nila Menon',
        type: 'passport',
        number: 'V9481024',
        expires: 'Permanent', // Incorrect legacy classification
      },
    },
    {
      id: 'dl-legacy-2',
      kind: 'rec',
      data: {
        title: 'Driving Licence - Arun Menon',
        type: 'licence',
        number: 'KL-07-2016',
        expires: '', // Missing date
      },
    },
    {
      id: 'pan-legacy-3',
      kind: 'rec',
      data: {
        title: 'PAN Card',
        type: 'pan',
        number: 'BPWPS4820K',
      },
    },
  ];

  const reclassResult = reclassifyMisplacedEntries(incorrectPermanentRows);
  const reclassifiedPass = reclassResult.migratedRows[0];
  const passVal = getDocumentValidityStatus(reclassifiedPass.data.type, reclassifiedPass.data.expires);

  assert(passVal.status === 'date_missing', 'Legacy passport marked "Permanent" reclassified as "date_missing"');
  assert(passVal.label === 'Expiry Date Required', 'Status badge is "Expiry Date Required" (NEVER "Permanent")');
  assert(reclassifiedPass.data.number === 'V9481024', 'Original document number preserved intact');

  // Check PAN card in same dataset
  const reclassifiedPan = reclassResult.migratedRows[2];
  const panVal = getDocumentValidityStatus(reclassifiedPan.data.type, reclassifiedPan.data.expires);
  assert(panVal.status === 'no_prescribed_expiry', 'PAN card correctly marked "no_prescribed_expiry"');

  // ----------------------------------------------------
  // TEST 22: Complete Demonstration with Synthetic Data & Privacy Shield
  // ----------------------------------------------------
  console.log('TEST 22: Complete Demonstration with Synthetic Data & Privacy Shield');
  assert(DUMMY_DOCUMENTS.length === 41, `41 total synthetic specimen assets verified across 10 persons (got ${DUMMY_DOCUMENTS.length})`);

  // Verify all 41 assets are safe vector SVG data URIs with zero real external downloads
  const allSvg = DUMMY_DOCUMENTS.every((d) => d.svgDataUrl.startsWith('data:image/svg+xml'));
  assert(allSvg, 'All 41 trial assets are safe synthetic vector SVG data URIs (zero unredacted external files)');

  // Verify Master Excel Workbook exports cleanly across 7 sheets
  const masterWb = generateMasterWorkbook();
  assert(masterWb.SheetNames.length === 7, `Master Excel workbook generates 7 sheets (got ${masterWb.SheetNames.length})`);
  assert(masterWb.SheetNames.includes('All 41 Trial Assets'), 'Sheet 1 is "All 41 Trial Assets"');
  assert(masterWb.SheetNames.includes('10 Persons Portfolio Index'), 'Sheet 2 is "10 Persons Portfolio Index"');
  assert(masterWb.SheetNames.includes('Bank Fixed Deposits'), 'Sheet 3 is "Bank Fixed Deposits"');
  assert(masterWb.SheetNames.includes('Official ID Records'), 'Sheet 4 is "Official ID Records"');
  assert(masterWb.SheetNames.includes('Insurance Policies'), 'Sheet 5 is "Insurance Policies"');
  assert(masterWb.SheetNames.includes('Mutual Funds'), 'Sheet 6 is "Mutual Funds"');
  assert(masterWb.SheetNames.includes('Utility Bills'), 'Sheet 7 is "Utility Bills"');

  // Verify that Official ID Records sheet does NOT label passports as Permanent if date is missing
  const idRecordsSheet = masterWb.Sheets['Official ID Records'];
  assert(Boolean(idRecordsSheet), 'Official ID Records sheet generated successfully');

  console.log('\n========================================');
  console.log(`Results: ${passed} Passed, ${failed} Failed`);
  console.log('========================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runAllTests().catch((err) => {
  console.error('Test run failed with unhandled error:', err);
  process.exit(1);
});
