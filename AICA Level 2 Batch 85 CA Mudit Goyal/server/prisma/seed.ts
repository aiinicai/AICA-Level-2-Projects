/**
 * Seed data for the demo.
 *
 * Idempotent — running it twice leaves the same database, so it is safe to
 * re-run before a demo without wiping anything first.
 */
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

const DEMO_PASSWORD = 'Capstone@2026';

const STAFF = [
  { staffName: 'Mudit Goyal', email: 'admin@capstone.local', designation: 'Partner', role: 'ADMIN' as const },
  { staffName: 'Anita Sharma', email: 'anita@capstone.local', designation: 'Senior Associate', role: 'STAFF' as const },
  { staffName: 'Rahul Verma', email: 'rahul@capstone.local', designation: 'Associate', role: 'STAFF' as const },
];

/** Midnight UTC of a date `daysAgo` before today — how @db.Date columns store a day. */
function dayOffset(daysAgo: number): Date {
  const d = new Date();
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - daysAgo));
}

/**
 * A timestamp at a given hour and minute IST on that day.
 *
 * `day` is midnight UTC — how a @db.Date column stores an IST calendar date —
 * so the IST offset has to come back off, or a punch meant for 09:45 in the
 * morning is stored as 09:45 UTC and reads as quarter past three in the
 * afternoon to anyone in India.
 */
const IST_OFFSET_MINUTES = 5 * 60 + 30;

function at(day: Date, hour: number, minute: number): Date {
  return new Date(day.getTime() + (hour * 60 + minute - IST_OFFSET_MINUTES) * 60_000);
}

async function main() {
  console.log('Seeding capstone demo data…');

  const hashed = await bcrypt.hash(DEMO_PASSWORD, 10);

  for (const person of STAFF) {
    const staff = await prisma.staff.upsert({
      where: { email: person.email },
      create: {
        staffName: person.staffName,
        email: person.email,
        designation: person.designation,
        joiningDate: dayOffset(400),
        phone: '+91 98765 43210',
      },
      update: { staffName: person.staffName, designation: person.designation },
    });

    await prisma.user.upsert({
      where: { email: person.email },
      create: { email: person.email, password: hashed, role: person.role, staffId: staff.id },
      update: { role: person.role, staffId: staff.id },
    });
  }

  const admin = await prisma.staff.findUniqueOrThrow({ where: { email: 'admin@capstone.local' } });
  const anita = await prisma.staff.findUniqueOrThrow({ where: { email: 'anita@capstone.local' } });

  // ── Attendance: a fortnight of punches, including one day split by lunch ──
  const everyone = await prisma.staff.findMany({ where: { isActive: true } });
  for (let back = 14; back >= 1; back--) {
    const day = dayOffset(back);
    if (day.getUTCDay() === 0) continue; // Sundays are not working days

    for (const staff of everyone) {
      // One person misses one day, so the register has something to show other
      // than a wall of PRESENT.
      if (staff.id === anita.id && back === 5) {
        await prisma.attendance.upsert({
          where: { staffId_date: { staffId: staff.id, date: day } },
          create: { staffId: staff.id, date: day, status: 'ON_LEAVE', notes: 'Casual leave' },
          update: {},
        });
        continue;
      }

      const existing = await prisma.attendance.findUnique({
        where: { staffId_date: { staffId: staff.id, date: day } },
      });
      if (existing) continue;

      // Wednesdays are broken by a lunch break — four punches, not two — which
      // is the case the punch model exists for.
      const splitDay = day.getUTCDay() === 3;
      const times: Array<{ direction: 'IN' | 'OUT'; punchedAt: Date }> = splitDay
        ? [
            { direction: 'IN', punchedAt: at(day, 9, 30) },
            { direction: 'OUT', punchedAt: at(day, 13, 0) },
            { direction: 'IN', punchedAt: at(day, 14, 0) },
            { direction: 'OUT', punchedAt: at(day, 18, 30) },
          ]
        : [
            { direction: 'IN', punchedAt: at(day, 9, 45) },
            { direction: 'OUT', punchedAt: at(day, 18, 15) },
          ];

      let workedMs = 0;
      for (let i = 0; i < times.length; i += 2) {
        workedMs += times[i + 1].punchedAt.getTime() - times[i].punchedAt.getTime();
      }

      await prisma.attendance.create({
        data: {
          staffId: staff.id,
          date: day,
          status: 'PRESENT',
          checkedInAt: times[0].punchedAt,
          checkOutAt: times[times.length - 1].punchedAt,
          workedMinutes: Math.round(workedMs / 60_000),
          punches: {
            create: times.map((t) => ({ staffId: staff.id, date: day, ...t })),
          },
        },
      });
    }
  }

  // ── Invoices ──────────────────────────────────────────────────────────────
  const alreadyBilled = await prisma.invoice.count();
  if (alreadyBilled === 0) {
    const samples = [
      {
        clientName: 'Sunrise Textiles Pvt Ltd',
        clientGstin: '27AABCS1429B1ZQ',
        clientState: 'Maharashtra',
        clientAddress: '14 Industrial Estate, Andheri East, Mumbai 400093',
        clientEmail: 'accounts@sunrisetextiles.example',
        taxType: 'IGST' as const,
        gstRate: 18,
        status: 'PAID' as const,
        daysAgo: 40,
        lines: [
          { description: 'Statutory audit for FY 2025-26', hsnSac: '998221', quantity: 1, rate: 125000 },
          { description: 'Out-of-pocket expenses', hsnSac: '998221', quantity: 1, rate: 8500 },
        ],
      },
      {
        clientName: 'Verma Constructions',
        clientGstin: '09AACCV3021K1Z8',
        clientState: 'Uttar Pradesh',
        clientAddress: 'Plot 22, Sector 62, Noida 201309',
        clientEmail: 'finance@vermaconstructions.example',
        taxType: 'IGST' as const,
        gstRate: 18,
        status: 'PARTIALLY_PAID' as const,
        daysAgo: 20,
        lines: [{ description: 'GST advisory and monthly return filing — Q1', hsnSac: '998231', quantity: 3, rate: 15000 }],
      },
      {
        clientName: 'Green Valley Farms LLP',
        clientGstin: '29AAFFG7654M1ZR',
        clientState: 'Karnataka',
        clientAddress: 'Survey 118, Hoskote Taluk, Bengaluru Rural 562114',
        clientEmail: 'admin@greenvalleyfarms.example',
        taxType: 'CGST_SGST' as const,
        gstRate: 18,
        status: 'SENT' as const,
        daysAgo: 8,
        lines: [
          { description: 'Income-tax return preparation and filing', hsnSac: '998222', quantity: 1, rate: 45000 },
          { description: 'Tax audit under section 44AB', hsnSac: '998222', quantity: 1, rate: 60000 },
        ],
      },
      {
        clientName: 'Kapoor & Sons Traders',
        clientState: 'Delhi',
        clientAddress: '3rd Floor, Karol Bagh, New Delhi 110005',
        taxType: 'NONE' as const,
        gstRate: 0,
        status: 'DRAFT' as const,
        daysAgo: 2,
        lines: [{ description: 'Bookkeeping retainer — current month', quantity: 1, rate: 18000 }],
      },
    ];

    const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;
    let serial = 1;

    for (const sample of samples) {
      const invoiceDate = dayOffset(sample.daysAgo);
      const lines = sample.lines.map((l, i) => ({
        slNo: i + 1,
        description: l.description,
        hsnSac: 'hsnSac' in l ? (l as { hsnSac?: string }).hsnSac ?? null : null,
        quantity: l.quantity,
        rate: l.rate,
        amount: r2(l.quantity * l.rate),
      }));
      const amount = r2(lines.reduce((s, l) => s + l.amount, 0));

      const half = r2(sample.gstRate / 2);
      const tax =
        sample.taxType === 'CGST_SGST'
          ? {
              cgstRate: half, sgstRate: half, igstRate: null,
              cgstAmount: r2(amount * (half / 100)), sgstAmount: r2(amount * (half / 100)), igstAmount: null,
            }
          : sample.taxType === 'IGST'
            ? {
                cgstRate: null, sgstRate: null, igstRate: sample.gstRate,
                cgstAmount: null, sgstAmount: null, igstAmount: r2(amount * (sample.gstRate / 100)),
              }
            : {
                cgstRate: null, sgstRate: null, igstRate: null,
                cgstAmount: null, sgstAmount: null, igstAmount: null,
              };

      const totalAmount = r2(
        amount + Number(tax.cgstAmount ?? 0) + Number(tax.sgstAmount ?? 0) + Number(tax.igstAmount ?? 0),
      );
      const paidAmount =
        sample.status === 'PAID' ? totalAmount : sample.status === 'PARTIALLY_PAID' ? r2(totalAmount * 0.4) : 0;

      const fyStart = invoiceDate.getUTCMonth() >= 3 ? invoiceDate.getUTCFullYear() : invoiceDate.getUTCFullYear() - 1;
      const fy = `${String(fyStart).slice(-2)}-${String(fyStart + 1).slice(-2)}`;

      const invoice = await prisma.invoice.create({
        data: {
          invoiceNumber: `MGSG/${fy}/${String(serial++).padStart(4, '0')}`,
          clientName: sample.clientName,
          clientGstin: 'clientGstin' in sample ? (sample as { clientGstin?: string }).clientGstin ?? null : null,
          clientAddress: sample.clientAddress,
          clientState: sample.clientState,
          clientEmail: 'clientEmail' in sample ? (sample as { clientEmail?: string }).clientEmail ?? null : null,
          invoiceDate,
          dueDate: new Date(invoiceDate.getTime() + 30 * 24 * 60 * 60 * 1000),
          amount,
          taxType: sample.taxType,
          ...tax,
          totalAmount,
          paidAmount,
          status: sample.status,
          createdById: admin.id,
          lineItems: { create: lines },
        },
      });

      if (paidAmount > 0) {
        await prisma.payment.create({
          data: {
            invoiceId: invoice.id,
            amount: paidAmount,
            paymentDate: dayOffset(Math.max(0, sample.daysAgo - 15)),
            mode: 'BANK',
            reference: `NEFT/${invoice.id}00${serial}`,
            createdById: admin.id,
          },
        });
      }
    }

    // The counter has to start after the numbers just handed out, or the first
    // invoice raised in the app collides with a seeded one.
    const latest = await prisma.invoice.findFirst({ orderBy: { id: 'desc' } });
    if (latest) {
      const fy = latest.invoiceNumber.split('/')[1];
      await prisma.invoiceSequence.upsert({
        where: { financialYear: fy },
        create: { financialYear: fy, nextNumber: serial },
        update: { nextNumber: serial },
      });
    }
  }

  const counts = {
    staff: await prisma.staff.count(),
    invoices: await prisma.invoice.count(),
    attendanceDays: await prisma.attendance.count(),
    punches: await prisma.attendancePunch.count(),
  };
  console.log('Seeded:', counts);
  console.log(`\nSign in with any of these — password: ${DEMO_PASSWORD}`);
  for (const s of STAFF) console.log(`  ${s.email.padEnd(24)} ${s.role}`);
}

main()
  .catch((err) => {
    console.error(err);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
