import fs from 'fs';
import path from 'path';
import sharp from 'sharp';

const samplesDir = path.resolve('public/samples');
if (!fs.existsSync(samplesDir)) {
  fs.mkdirSync(samplesDir, { recursive: true });
}

// 1. Handwritten Tea Stall Bill (Notebook lined paper style, handwritten cursive feel)
const handwrittenTeaBillSvg = `
<svg width="600" height="750" viewBox="0 0 600 750" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Paper texture gradient -->
    <linearGradient id="paper" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fdfbf7"/>
      <stop offset="100%" stop-color="#f4eee1"/>
    </linearGradient>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000000" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Sheet of Paper -->
  <rect x="30" y="30" width="540" height="690" rx="12" fill="url(#paper)" stroke="#dcd3c0" stroke-width="2" filter="url(#shadow)"/>
  
  <!-- Red margin line on left -->
  <line x1="100" y1="40" x2="100" y2="710" stroke="#f87171" stroke-width="2" stroke-opacity="0.6"/>
  
  <!-- Blue notebook ruling lines -->
  ${Array.from({ length: 14 }).map((_, i) => `
    <line x1="40" y1="${130 + i * 40}" x2="560" y2="${130 + i * 40}" stroke="#93c5fd" stroke-width="1.5" stroke-opacity="0.5"/>
  `).join('')}

  <!-- Handwritten Text (Ink Blue #1e3a8a, slight natural rotation) -->
  <g fill="#1e3a8a" font-family="'Comic Sans MS', 'Caveat', cursive, sans-serif">
    <!-- Header -->
    <text x="300" y="80" font-size="28" font-weight="bold" text-anchor="middle" transform="rotate(-1 300 80)">SHARMA TEA STALL &amp; SNACKS</text>
    <text x="300" y="110" font-size="16" text-anchor="middle" fill="#4b5563">MG Road, Near Metro Gate 2</text>
    
    <!-- Date and Bill No -->
    <text x="115" y="165" font-size="18" font-weight="bold">Date: 24/09/2026</text>
    <text x="420" y="165" font-size="18" font-weight="bold">Bill No: #42</text>

    <!-- Column Headers -->
    <text x="115" y="205" font-size="18" font-weight="bold" text-decoration="underline">Item Particulars</text>
    <text x="380" y="205" font-size="18" font-weight="bold" text-decoration="underline">Qty</text>
    <text x="480" y="205" font-size="18" font-weight="bold" text-decoration="underline">Rs.</text>

    <!-- Line items in casual handwriting -->
    <text x="115" y="245" font-size="20">1. Special Masala Chai</text>
    <text x="390" y="245" font-size="20">4</text>
    <text x="490" y="245" font-size="20">80</text>

    <text x="115" y="285" font-size="20">2. Bun Maska</text>
    <text x="390" y="285" font-size="20">2</text>
    <text x="490" y="285" font-size="20">60</text>

    <text x="115" y="325" font-size="20">3. Aloo Samosa</text>
    <text x="390" y="325" font-size="20">2</text>
    <text x="490" y="325" font-size="20">40</text>

    <!-- Total divider line -->
    <line x1="110" y1="380" x2="540" y2="380" stroke="#1e3a8a" stroke-width="2.5"/>
    <line x1="110" y1="435" x2="540" y2="435" stroke="#1e3a8a" stroke-width="2.5"/>

    <!-- Total -->
    <text x="115" y="415" font-size="24" font-weight="bold">Total Amount Paid</text>
    <text x="475" y="415" font-size="26" font-weight="bold">₹ 180/-</text>

    <text x="115" y="480" font-size="18" font-style="italic">Paid via PhonePe UPI (Ref: 62891)</text>
    <text x="300" y="550" font-size="20" text-anchor="middle" fill="#047857">** Thank you! Visit Again **</text>
  </g>

  <!-- Green "PAID VIA UPI" Rubber Stamp effect -->
  <g transform="translate(360, 560) rotate(-12)">
    <rect x="-10" y="-10" width="180" height="60" rx="8" fill="none" stroke="#059669" stroke-width="4" stroke-dasharray="8 3" opacity="0.85"/>
    <text x="80" y="28" font-family="Arial, sans-serif" font-size="22" font-weight="900" fill="#059669" text-anchor="middle" opacity="0.85">PAID (UPI)</text>
  </g>
</svg>
`;

// 2. Supermarket / Grocery Thermal Shopping Receipt
const shoppingBillSvg = `
<svg width="600" height="850" viewBox="0 0 600 850" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="receiptShadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="#000" flood-opacity="0.12"/>
    </filter>
  </defs>

  <!-- Thermal Paper Roll Base -->
  <rect x="50" y="25" width="500" height="800" fill="#ffffff" stroke="#e5e7eb" stroke-width="1.5" filter="url(#receiptShadow)"/>
  
  <!-- Serrated top/bottom zigzag border -->
  <path d="M50 25 L65 15 L80 25 L95 15 L110 25 L125 15 L140 25 L155 15 L170 25 L185 15 L200 25 L215 15 L230 25 L245 15 L260 25 L275 15 L290 25 L305 15 L320 25 L335 15 L350 25 L365 15 L380 25 L395 15 L410 25 L425 15 L440 25 L455 15 L470 25 L485 15 L500 25 L515 15 L530 25 L545 15 L550 25 Z" fill="#ffffff"/>

  <g font-family="'Courier New', Courier, monospace" fill="#111827">
    <!-- Supermarket Header -->
    <text x="300" y="80" font-size="26" font-weight="bold" text-anchor="middle">RELIANCE SMART SUPERSTORE</text>
    <text x="300" y="105" font-size="14" text-anchor="middle">Store #4088, Nexus Mall, Koramangala</text>
    <text x="300" y="125" font-size="14" text-anchor="middle">GSTIN: 29AABCR1234F1Z8</text>
    <text x="300" y="145" font-size="14" text-anchor="middle">TAX INVOICE / CASH RECEIPT</text>

    <!-- Separator -->
    <text x="300" y="170" font-size="14" text-anchor="middle">--------------------------------------------------</text>

    <!-- Metadata -->
    <text x="80" y="195" font-size="14">Date: 2026-09-22 17:42</text>
    <text x="360" y="195" font-size="14">POS: 04  Cashier: Rahul</text>
    <text x="80" y="215" font-size="14">Invoice No: INV-2026-88491</text>
    <text x="360" y="215" font-size="14">Items: 5</text>

    <text x="300" y="240" font-size="14" text-anchor="middle">==================================================</text>

    <!-- Items Header -->
    <text x="80" y="265" font-size="15" font-weight="bold">ITEM DESCRIPTION</text>
    <text x="350" y="265" font-size="15" font-weight="bold">QTY</text>
    <text x="460" y="265" font-size="15" font-weight="bold">AMOUNT</text>

    <text x="300" y="285" font-size="14" text-anchor="middle">--------------------------------------------------</text>

    <!-- Items -->
    <text x="80" y="315" font-size="15">Daawat Basmati Rice (5kg)</text>
    <text x="360" y="315" font-size="15">1</text>
    <text x="460" y="315" font-size="15">450.00</text>

    <text x="80" y="355" font-size="15">Figaro Extra Olive Oil (1L)</text>
    <text x="360" y="355" font-size="15">1</text>
    <text x="460" y="355" font-size="15">820.00</text>

    <text x="80" y="395" font-size="15">Surf Excel Matic Top Load (2kg)</text>
    <text x="360" y="395" font-size="15">1</text>
    <text x="460" y="395" font-size="15">390.00</text>

    <text x="80" y="435" font-size="15">Amul Pure Cow Ghee (1L)</text>
    <text x="360" y="435" font-size="15">1</text>
    <text x="460" y="435" font-size="15">580.00</text>

    <text x="80" y="475" font-size="15">Cadbury Bournville Dark Choc</text>
    <text x="360" y="475" font-size="15">2</text>
    <text x="460" y="475" font-size="15">210.00</text>

    <text x="300" y="515" font-size="14" text-anchor="middle">--------------------------------------------------</text>

    <text x="80" y="545" font-size="15">Subtotal</text>
    <text x="440" y="545" font-size="15">₹ 2,450.00</text>

    <text x="80" y="575" font-size="15">Store Club Member Discount</text>
    <text x="440" y="575" font-size="15">-₹ 580.00</text>

    <text x="80" y="605" font-size="15">CGST 2.5% + SGST 2.5%</text>
    <text x="440" y="605" font-size="15">₹ 93.50</text>

    <text x="300" y="635" font-size="14" text-anchor="middle">==================================================</text>

    <!-- Grand Total -->
    <text x="80" y="670" font-size="20" font-weight="bold">NET PAYABLE TOTAL</text>
    <text x="400" y="670" font-size="22" font-weight="bold">₹ 1,870.00</text>

    <text x="300" y="705" font-size="14" text-anchor="middle">--------------------------------------------------</text>

    <!-- Payment info -->
    <text x="80" y="730" font-size="14">Payment Mode: HDFC Visa Card ending 4821</text>
    <text x="80" y="750" font-size="14">Auth Code: 894103  Txn ID: 902847291</text>

    <!-- Barcode simulation -->
    <rect x="150" y="775" width="300" height="25" fill="#111827"/>
    <text x="300" y="815" font-size="13" text-anchor="middle">THANK YOU FOR SHOPPING WITH US</text>
  </g>
</svg>
`;

// 3. Mutual Fund SIP Investment Statement
const investmentStatementSvg = `
<svg width="700" height="900" viewBox="0 0 700 900" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="statementShadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.1"/>
    </filter>
  </defs>

  <!-- Document Page Base -->
  <rect x="40" y="30" width="620" height="840" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5" filter="url(#statementShadow)"/>

  <!-- Top Brand Banner (HDFC Mutual Fund Style) -->
  <rect x="40" y="30" width="620" height="90" rx="10" fill="#1e3a8a"/>
  
  <g fill="#ffffff">
    <text x="75" y="75" font-family="Arial, sans-serif" font-size="24" font-weight="bold">HDFC MUTUAL FUND</text>
    <text x="75" y="100" font-family="Arial, sans-serif" font-size="14" fill="#93c5fd">MUTUAL FUND SIP TRANSACTION CONFIRMATION STATEMENT</text>
  </g>

  <g font-family="Arial, sans-serif" fill="#1e293b">
    <!-- Investor & Folio Details Grid -->
    <rect x="70" y="145" width="560" height="110" rx="8" fill="#f8fafc" stroke="#e2e8f0"/>
    
    <text x="90" y="175" font-size="13" font-weight="bold" fill="#64748b">INVESTOR NAME:</text>
    <text x="210" y="175" font-size="14" font-weight="bold">PRIYA SHARMA</text>

    <text x="90" y="205" font-size="13" font-weight="bold" fill="#64748b">FOLIO NUMBER:</text>
    <text x="210" y="205" font-size="14" font-weight="bold">91827462 / 44</text>

    <text x="90" y="235" font-size="13" font-weight="bold" fill="#64748b">PAN / KYC STATUS:</text>
    <text x="210" y="235" font-size="13" fill="#059669" font-weight="bold">ABCPS1234K (Verified)</text>

    <text x="390" y="175" font-size="13" font-weight="bold" fill="#64748b">DATE OF ALLOTMENT:</text>
    <text x="540" y="175" font-size="14" font-weight="bold">2026-09-23</text>

    <text x="390" y="205" font-size="13" font-weight="bold" fill="#64748b">TRANSACTION TYPE:</text>
    <text x="540" y="205" font-size="14" font-weight="bold">Systematic SIP</text>

    <text x="390" y="235" font-size="13" font-weight="bold" fill="#64748b">PAYMENT MODE:</text>
    <text x="540" y="235" font-size="14" font-weight="bold">Bank Auto-Debit</text>

    <!-- Scheme Details Card -->
    <rect x="70" y="280" width="560" height="230" rx="8" fill="#ffffff" stroke="#cbd5e1"/>
    <rect x="70" y="280" width="560" height="40" rx="8" fill="#0f766e"/>
    <text x="90" y="306" font-size="15" font-weight="bold" fill="#ffffff">INVESTMENT SCHEME SUMMARY</text>

    <text x="90" y="345" font-size="14" font-weight="bold" fill="#475569">Scheme Name:</text>
    <text x="90" y="370" font-size="16" font-weight="bold" fill="#0f766e">HDFC Index Fund - Nifty 50 Plan - Growth Direct</text>

    <line x1="90" y1="395" x2="610" y2="395" stroke="#f1f5f9" stroke-width="2"/>

    <text x="90" y="425" font-size="13" font-weight="bold" fill="#64748b">Allotment NAV (INR):</text>
    <text x="90" y="450" font-size="18" font-weight="bold">₹ 184.2025</text>

    <text x="280" y="425" font-size="13" font-weight="bold" fill="#64748b">Units Allotted:</text>
    <text x="280" y="450" font-size="18" font-weight="bold">135.720</text>

    <text x="450" y="425" font-size="13" font-weight="bold" fill="#64748b">Gross Investment Amount:</text>
    <text x="450" y="450" font-size="24" font-weight="bold" fill="#059669">₹ 25,000.00</text>

    <text x="90" y="485" font-size="12" fill="#64748b">STT / Stamp Duty: ₹1.25 | Net Capital Amount: ₹24,998.75</text>

    <!-- Performance & Valuation table -->
    <rect x="70" y="530" width="560" height="150" rx="8" fill="#f0fdf4" stroke="#86efac"/>
    <text x="90" y="565" font-size="15" font-weight="bold" fill="#166534">Cumulative Portfolio Holding in this Folio</text>

    <text x="90" y="600" font-size="13" fill="#374151">Total Units Held:</text>
    <text x="240" y="600" font-size="14" font-weight="bold">1,842.604</text>

    <text x="90" y="630" font-size="13" fill="#374151">Total Amount Invested:</text>
    <text x="240" y="630" font-size="14" font-weight="bold">₹ 3,25,000.00</text>

    <text x="380" y="600" font-size="13" fill="#374151">Current Valuation:</text>
    <text x="500" y="600" font-size="16" font-weight="bold" fill="#166534">₹ 4,12,850.00</text>

    <text x="380" y="630" font-size="13" fill="#374151">XIRR Return:</text>
    <text x="500" y="630" font-size="15" font-weight="bold" fill="#166534">+16.4% p.a.</text>

    <!-- Footer Security Notice -->
    <rect x="70" y="700" width="560" height="90" rx="8" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="90" y="730" font-size="12" fill="#64748b">This is a system generated statement issued by Registrar &amp; Transfer Agent (CAMS).</text>
    <text x="90" y="750" font-size="12" fill="#64748b">Mutual Fund investments are subject to market risks. Read all scheme related documents carefully.</text>
    <text x="90" y="770" font-size="12" font-weight="bold" fill="#1e3a8a">Support Contact: 1800 3010 6767 | www.hdfcfund.com</text>

    <text x="350" y="835" font-size="11" text-anchor="middle" fill="#94a3b8">Page 1 of 1 • Generated electronically on 23-Sep-2026</text>
  </g>
</svg>
`;

// 4. Flight Booking Tax Invoice / E-Ticket (IndiGo Airlines Style)
const flightInvoiceSvg = `
<svg width="700" height="880" viewBox="0 0 700 880" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="flightShadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.12"/>
    </filter>
  </defs>

  <!-- Ticket Page Base -->
  <rect x="40" y="30" width="620" height="820" rx="12" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5" filter="url(#flightShadow)"/>

  <!-- Indigo Blue Header -->
  <rect x="40" y="30" width="620" height="95" rx="12" fill="#001b94"/>
  
  <g fill="#ffffff" font-family="Arial, sans-serif">
    <text x="75" y="75" font-size="28" font-weight="900" letter-spacing="1">IndiGo</text>
    <text x="75" y="105" font-size="13" font-weight="bold" fill="#93c5fd">PASSENGER ITINERARY &amp; GST TAX INVOICE</text>
    
    <text x="590" y="65" font-size="12" text-anchor="end" fill="#93c5fd">BOOKING REFERENCE (PNR)</text>
    <text x="590" y="95" font-size="24" font-weight="900" text-anchor="end" fill="#facc15">6E-R84K92</text>
  </g>

  <g font-family="Arial, sans-serif" fill="#1e293b">
    <!-- Flight Route Banner -->
    <rect x="70" y="145" width="560" height="110" rx="8" fill="#eff6ff" stroke="#bfdbfe"/>
    
    <text x="100" y="185" font-size="24" font-weight="bold">BOM</text>
    <text x="100" y="210" font-size="13" fill="#64748b">Mumbai (T2)</text>
    <text x="100" y="235" font-size="13" font-weight="bold" fill="#001b94">20 Sep 2026, 06:15 AM</text>

    <!-- Arrow icon in center -->
    <text x="350" y="195" font-size="22" text-anchor="middle" fill="#001b94">✈ ——————&gt;</text>
    <text x="350" y="225" font-size="12" font-weight="bold" text-anchor="middle" fill="#64748b">6E-5312 (Non-Stop, 2h 10m)</text>

    <text x="530" y="185" font-size="24" font-weight="bold" text-anchor="end">DEL</text>
    <text x="530" y="210" font-size="13" fill="#64748b" text-anchor="end">New Delhi (T1)</text>
    <text x="530" y="235" font-size="13" font-weight="bold" fill="#001b94" text-anchor="end">20 Sep 2026, 08:25 AM</text>

    <!-- Passenger Info -->
    <rect x="70" y="275" width="560" height="75" rx="8" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="90" y="305" font-size="12" font-weight="bold" fill="#64748b">PASSENGER NAME</text>
    <text x="90" y="330" font-size="15" font-weight="bold">1. MS. PRIYA SHARMA</text>

    <text x="350" y="305" font-size="12" font-weight="bold" fill="#64748b">SEAT</text>
    <text x="350" y="330" font-size="15" font-weight="bold">12F (Window)</text>

    <text x="490" y="305" font-size="12" font-weight="bold" fill="#64748b">CABIN BAG</text>
    <text x="490" y="330" font-size="15" font-weight="bold">7 Kg + 15 Kg Check-in</text>

    <!-- Fare Breakdown Table -->
    <rect x="70" y="370" width="560" height="240" rx="8" fill="#ffffff" stroke="#cbd5e1"/>
    <rect x="70" y="370" width="560" height="35" rx="8" fill="#001b94"/>
    <text x="90" y="393" font-size="13" font-weight="bold" fill="#ffffff">AIRFARE BREAKDOWN (TAX INVOICE)</text>
    <text x="610" y="393" font-size="13" font-weight="bold" text-anchor="end" fill="#ffffff">AMOUNT (INR)</text>

    <text x="90" y="430" font-size="14">Airfare Charges (Base Fare)</text>
    <text x="610" y="430" font-size="14" text-anchor="end">₹ 4,850.00</text>

    <text x="90" y="465" font-size="14">Aviation Security &amp; User Dev Fee (UDF)</text>
    <text x="610" y="465" font-size="14" text-anchor="end">₹ 480.00</text>

    <text x="90" y="500" font-size="14">Fuel Surcharge (YQ)</text>
    <text x="610" y="500" font-size="14" text-anchor="end">₹ 670.00</text>

    <text x="90" y="535" font-size="14">Goods and Services Tax (GST 5%)</text>
    <text x="610" y="535" font-size="14" text-anchor="end">₹ 285.00</text>

    <line x1="90" y1="555" x2="610" y2="555" stroke="#cbd5e1" stroke-width="1.5"/>

    <!-- Grand Total -->
    <text x="90" y="585" font-size="18" font-weight="bold" fill="#001b94">TOTAL INVOICE AMOUNT PAID</text>
    <text x="610" y="585" font-size="22" font-weight="bold" text-anchor="end" fill="#001b94">₹ 6,285.00</text>

    <!-- Payment info & Invoice metadata -->
    <rect x="70" y="630" width="560" height="90" rx="8" fill="#f8fafc" stroke="#e2e8f0"/>
    <text x="90" y="660" font-size="13"><strong>Merchant:</strong> InterGlobe Aviation Ltd (IndiGo)</text>
    <text x="360" y="660" font-size="13"><strong>Invoice No:</strong> 6E-INV-2026-99214</text>
    <text x="90" y="685" font-size="13"><strong>Date of Issue:</strong> 2026-09-20</text>
    <text x="360" y="685" font-size="13"><strong>Payment Mode:</strong> Card (HDFC Visa)</text>
    <text x="90" y="708" font-size="12" fill="#059669" font-weight="bold">✓ Payment Status: Successful / Confirmed</text>

    <!-- Barcode simulation -->
    <rect x="180" y="740" width="340" height="35" fill="#001b94"/>
    <text x="350" y="800" font-size="12" text-anchor="middle" fill="#64748b">Gate closes 25 minutes prior to departure • www.goindigo.in</text>
  </g>
</svg>
`;

async function generate() {
  await sharp(Buffer.from(handwrittenTeaBillSvg)).png().toFile(path.join(samplesDir, 'handwritten-tea-bill.png'));
  await sharp(Buffer.from(shoppingBillSvg)).png().toFile(path.join(samplesDir, 'shopping-bill.png'));
  await sharp(Buffer.from(investmentStatementSvg)).png().toFile(path.join(samplesDir, 'investment-statement.png'));
  await sharp(Buffer.from(flightInvoiceSvg)).png().toFile(path.join(samplesDir, 'flight-invoice.png'));

  console.log('Sample test images created in /public/samples/');
}

generate().catch(console.error);
