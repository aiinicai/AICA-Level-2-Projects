# 3CD Helper – आगे की योजना (25-11-2026)

यह फ़ाइल यूज़र (Yash Associates) के साथ हुई चर्चा में तय बातों का रिकॉर्ड है।

**स्थिति (25-11-2026): भाग 1 से 4 बन गए हैं।**
- छोटे काम (Clause 31 का ज़िक्र, bulk mode, "Only loan groups" – connector 1.0.3, कई फ़ाइलें एक साथ): commit 82f8fbc
- Clause 44 का नया ledger-wise तरीका: commit 1a141dc
- एक जगह से import ("Bring data (all clauses)"): इसके बाद वाला commit
- Database में कोई बदलाव नहीं (expense_rows, engagements.clause_answers.c44_books, column_mappings "c44_ledger_method")
- Tally के field नाम Aeron के Master.xml से पक्के किए: GSTREGISTRATIONTYPE, PARTYGSTIN / LEDGSTREGDETAILS.GSTIN, GSTDETAILS.TAXABILITY
शर्तें: सब कुछ बिना खर्च वाला, ऐप बिना AI के चले, database बदलाव हो तो सिर्फ़ Lovable chat से (1 credit)।

## अब तक बना हुआ (सन्दर्भ के लिए)
- Clause 31 (269SS / 269T), Clause 44, ZIP upload, client delete, file delete
- WhatsApp पर रिपोर्ट भेजना (7 दिन का link)
- Tally Connector (Chrome extension) 1.0.2 – Clause 31 में "Day Book / Only Unsecured Loans", Clause 44 में Day Book
- Client upload link (7 दिन, बिना login) – **Lovable में DB बदलाव अभी बाकी** (`docs/database/client_upload_links.sql`)

## यूज़र के फ़ैसले (Clause 44)
- Salary, wages, ESIC/PF और government fees → Clause 44 से **बाहर**
- Bank charges → **अंदर** (setting: "Bank charges = Regular registered", बदली जा सके)
- Depreciation, provisions, write-offs आदि → बाहर (Guidance Note / आम प्रैक्टिस)
- Capital + revenue दोनों खर्च (Guidance Note: capital expenditure भी इसी format में)
- Fixed Asset ledger में सीधी entry = capital expenditure। Party हो तो उसका GST status; नकद / सीधी बैंक entry और party न हो → **Unregistered**

## 1. एक ही जगह से import (नया)
- Assessment year खोलते ही ऊपर "डेटा लाएँ" – पहले पूछे: **कौन-कौन से clause तैयार करने हैं** (☐ Clause 44 ☐ Clause 31 …)
- Tally Connector **एक ही बार** में ज़रूरी data लाए (masters + चुने clause के हिसाब से vouchers), फिर हर clause अपनी रिपोर्ट बनाए
- Connector के विकल्प:
  - Clause 31: "सिर्फ़ लोन groups" = Loans (Liability) और उसके अंदर के सारे groups (Secured, Unsecured…), group चुनने की सुविधा; या पूरी Day Book
  - Clause 44: "सिर्फ़ खर्च और Fixed Assets ledgers"; या पूरी Day Book
  - दोनों चुने हों तो दोनों के ledgers का जोड़ एक बार में
- फ़ाइल upload भी इसी जगह से, **एक से ज़्यादा फ़ाइलें एक साथ** (अभी एक बार में 1 फ़ाइल; कई फ़ाइलें सिर्फ़ ZIP में डालकर जाती हैं)
- हर clause के अपने Upload tab में भी विकल्प बना रहे (पुराना तरीका टूटे नहीं)

## 2. Clause 44 – नया तरीका (Day Book की हर line वाली उलझन ख़त्म)
1. **Ledger चुनें**: Tally के groups का पेड़ (accounts chart अलग screen नहीं, यहीं दिखेगा) – Purchase Accounts, Direct Expenses, Indirect Expenses (revenue) और Fixed Assets (capital) अपने-आप चुने; बाहर रखने वाले ledgers (ऊपर फ़ैसले) की tick हटी; यूज़र बदल सके
2. **Party से जोड़ना**: हर खर्च → voucher की party; party न हो (नकद / बैंक) → Unregistered
3. **Party का GST status**:
   1. पहले Tally ledger master (GSTIN, registration type: Regular / Composition / Unregistered)
   2. फिर GSTR-2B से मिलान (ऐप पहले से 2B JSON पढ़ता है) – GSTIN किताबों में है पर 2B में कभी नहीं, या हर bill में GST शून्य → **Review** mark
   3. Review वाली party पर "GST portal पर देखें" link – यूज़र captcha भरकर status देखे और ऐप में चुने; status party master में सेव (दूसरे साल / क्लाइंट में दोबारा न देखना पड़े)
   - Python / अपने-आप portal पढ़ना: नहीं (ऐप में Python नहीं चलता, अलग server का खर्च; captcha पार करना portal की शर्तों के ख़िलाफ़; GSP API पैसे वाली)
4. **Exempt**: expense ledger की GST taxability (Exempt / Nil / Non-GST) से
5. **रकम**: सिर्फ़ खर्च की रकम; Input GST अलग; debit note / purchase return खर्च घटाए – plus/minus वाली उलझन नहीं
6. **रिपोर्ट**:
   - पहले **हर ledger अलग-अलग** (P&L के सारे खर्च वाले accounts और capital expenditure के accounts), हर ledger की पंक्ति: कुल | Exempt | Composition | Regular | Unregistered – ताकि जाँच सकें
   - ledger खोलने पर party-wise ब्योरा
   - फिर **सबका जोड़** – Form 3CD Clause 44 की तालिका
   - नीचे P&L से reconciliation (Guidance Note 2023 वाला working paper)
- Connector को ledger masters से GST registration type और taxability पढ़नी होगी (field के नाम live Tally पर जाँचने हैं)

## 3. Clause 31 – छोटे सुधार
- Entries में ऊपर tick करके **एक साथ mode बदलना** (Electronic / a/c payee cheque / cash …)। 3CD में NEFT / RTGS अलग नहीं पूछे जाते – दोनों "Electronic"
- Connector का "Only Unsecured Loans" → "सिर्फ़ लोन groups" (ऊपर)

## 4. ऐप में Clause 31 का ज़िक्र (अभी सिर्फ़ Clause 44 लिखा आता है)
- Landing page (hero, features, FAQ – "Clause 31 roadmap पर है" ग़लत है), login screen, dashboard का खाली-स्थिति वाला text, client के "Assessment years" का subtitle, page description / meta, `public/manifest.webmanifest`
- सब जगह "Clause 44 और Clause 31" (और आगे के clauses) – app का नाम "3CD Helper" वही

## 5. Taskbar पर pin किया ऐप
- Connector सिर्फ़ उसी Chrome profile में चलता है जहाँ लगाया है। Pin वाला ऐप दूसरे browser / profile में खुल रहा था
- उपाय (कोड नहीं): उसी Chrome में ऐप खोलकर ⋮ → Cast, save and share → "Install page as app", फिर pin
- आगे चाहें तो Firefox वाला connector अलग से

## लागत
- ऊपर के सब हिस्सों में नई DB table की ज़रूरत नहीं लगती (बनाते समय पक्का करना है) → Lovable credit नहीं
- Client upload link वाला DB बदलाव अलग से बाकी है

## क्रम (सुझाव)
1. छोटे काम: Clause 31 का ज़िक्र सब जगह, bulk mode, "सिर्फ़ लोन groups", कई फ़ाइलें एक साथ
2. एक जगह से import + clause चुनना
3. Clause 44 का नया तरीका और ledger-wise रिपोर्ट
