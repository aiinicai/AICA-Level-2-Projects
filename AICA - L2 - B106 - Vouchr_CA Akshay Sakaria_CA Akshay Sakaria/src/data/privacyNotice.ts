// Privacy notice shown at sign-on (DPDP Act 2023 s.5; DPDP Rules 2025 r.3): standalone, plain language, itemised personal
// data, purposes, how to withdraw / exercise rights / complain to the Board. English and Hindi (s.5(3)).
// Placeholders: {firm} {client} {contact}. Draft for the firm's legal review — see PRIVACY-DPDP.md.

export interface NoticeSection { title: string; points: string[] }

export const NOTICE: Record<'en' | 'hi', { heading: string; intro: string; sections: NoticeSection[] }> = {
  en: {
    heading: 'Privacy notice — how Vouchr uses personal data',
    intro: 'Vouchr is run by {firm}, the chartered accountants for {client}. For {client}’s business records, {firm} works on {client}’s behalf. Please read this before you agree.',
    sections: [
      { title: 'Personal data we process', points: [
        'Your account: name, role, company, sign-in details, chosen language, and a record of actions you take in the app (audit trail).',
        'Bills and documents you upload: photos and PDFs, which may show names, addresses, GSTIN, PAN, phone numbers and signatures of vendors.',
        'Payment details you enter: amounts, dates, UPI IDs, bank account names, cheque and UTR numbers.',
        'Voice recordings — only if you use voice entry.',
        'Your WhatsApp number and the bills you send to the firm’s WhatsApp number — only if your admin adds your number and you confirm it.',
        'Technical details needed for security, such as the time of sign-in.'
      ] },
      { title: 'Why we use it', points: [
        'To record and classify {client}’s business expenses and payments.',
        'For GST and TDS compliance and returns prepared by {firm}.',
        'For payment reminders, reports, Tally posting and audit trail.',
        'To detect errors, duplicate or fake bills, and to keep the app secure.'
      ] },
      { title: 'AI assistance (optional — your choice)', points: [
        'Only if you agree: specific bills, voice recordings, notices or text are sent to Google Gemini, a paid service, to read them and suggest entries.',
        'Google states it does not use paid-service content to improve its products; it keeps request logs for a limited period. Processing may take place outside India.',
        'Every AI result is checked by rules and reviewed by people. Anything doubtful is marked. Nothing is final on AI output alone.',
        'You can use Vouchr without AI. You can switch AI off at any time.'
      ] },
      { title: 'Where it is kept and who receives it', points: [
        'Documents: a Google Drive folder kept by {firm} for {client}. Records: the Vouchr database host.',
        'Google Gemini — only if AI is agreed. WhatsApp (Meta) — only for bills you choose to send by WhatsApp. Tally — {client}’s own books. Tax authorities — when returns are filed as the law requires.',
        'Your data is never sold and never used for advertising.'
      ] },
      { title: 'How long', points: [
        'While the engagement between {client} and {firm} continues.',
        'After that, only for as long as tax laws require business records to be kept (for example, GST law requires accounts to be kept for 72 months from the due date of the annual return), and then deleted.',
        'Security logs are kept for at least one year, as the DPDP Rules require.'
      ] },
      { title: 'Your rights and how to use them', points: [
        'Ask for a summary of your personal data, correct or update it, ask for erasure (subject to records the law requires us to keep), raise a grievance, or nominate someone to act for you.',
        'Use “Privacy & consent” in the app, or contact {contact}. We reply within 90 days at most.',
        'If you are not satisfied, you may complain to the Data Protection Board of India.'
      ] },
      { title: 'Withdrawing consent', points: [
        'You can withdraw at any time from “Privacy & consent” — one tap, as easy as agreeing.',
        'Withdrawal stops further use of your data based on consent; it does not affect what was done before. Records the law requires are still kept.',
        'Without consent you cannot use the app. Your consent stays valid until the engagement ends, unless you withdraw it earlier.'
      ] }
    ]
  },
  hi: {
    heading: 'गोपनीयता सूचना — Vouchr व्यक्तिगत डेटा का उपयोग कैसे करता है',
    intro: 'Vouchr को {firm} चलाता है, जो {client} के चार्टर्ड अकाउंटेंट हैं। {client} के व्यावसायिक रिकॉर्ड के लिए {firm}, {client} की ओर से काम करता है। सहमति देने से पहले कृपया इसे पढ़ें।',
    sections: [
      { title: 'हम कौन-सा व्यक्तिगत डेटा उपयोग करते हैं', points: [
        'आपका खाता: नाम, भूमिका, कंपनी, साइन-इन विवरण, चुनी गई भाषा, और ऐप में आपके कार्यों का रिकॉर्ड (ऑडिट ट्रेल)।',
        'आपके अपलोड किए बिल और दस्तावेज़: फोटो और PDF, जिनमें विक्रेताओं के नाम, पते, GSTIN, PAN, फ़ोन नंबर और हस्ताक्षर हो सकते हैं।',
        'आपके दर्ज भुगतान विवरण: राशि, तारीख, UPI ID, बैंक खाते के नाम, चेक और UTR नंबर।',
        'आवाज़ की रिकॉर्डिंग — केवल तब, जब आप बोलकर एंट्री करें।',
        'आपका WhatsApp नंबर और फ़र्म के WhatsApp नंबर पर भेजे गए बिल — केवल तब, जब एडमिन आपका नंबर जोड़े और आप उसकी पुष्टि करें।',
        'सुरक्षा के लिए ज़रूरी तकनीकी विवरण, जैसे साइन-इन का समय।'
      ] },
      { title: 'हम इसका उपयोग क्यों करते हैं', points: [
        '{client} के व्यावसायिक खर्च और भुगतान दर्ज करने और वर्गीकृत करने के लिए।',
        '{firm} द्वारा तैयार किए जाने वाले GST और TDS अनुपालन और रिटर्न के लिए।',
        'भुगतान रिमाइंडर, रिपोर्ट, Tally पोस्टिंग और ऑडिट ट्रेल के लिए।',
        'गलतियाँ, दोहरे या नकली बिल पकड़ने और ऐप को सुरक्षित रखने के लिए।'
      ] },
      { title: 'AI सहायता (वैकल्पिक — आपकी मर्ज़ी)', points: [
        'केवल आपकी सहमति पर: कुछ बिल, आवाज़ की रिकॉर्डिंग, नोटिस या टेक्स्ट Google Gemini (पेड सेवा) को पढ़ने और एंट्री सुझाने के लिए भेजे जाते हैं।',
        'Google के अनुसार पेड सेवा की सामग्री उसके उत्पाद सुधारने में इस्तेमाल नहीं होती; वह अनुरोध के लॉग कुछ समय तक रखता है। प्रोसेसिंग भारत के बाहर भी हो सकती है।',
        'AI का हर नतीजा नियमों से जाँचा जाता है और लोग उसे देखते हैं। जिस पर शक हो, उसे चिह्नित किया जाता है। केवल AI के भरोसे कुछ अंतिम नहीं होता।',
        'आप बिना AI के भी Vouchr इस्तेमाल कर सकते हैं। AI कभी भी बंद कर सकते हैं।'
      ] },
      { title: 'डेटा कहाँ रखा जाता है और किसे मिलता है', points: [
        'दस्तावेज़: {firm} द्वारा {client} के लिए रखा गया Google Drive फ़ोल्डर। रिकॉर्ड: Vouchr का डेटाबेस होस्ट।',
        'Google Gemini — केवल AI की सहमति होने पर। WhatsApp (Meta) — केवल उन बिलों के लिए जो आप WhatsApp से भेजें। Tally — {client} की अपनी बहियाँ। कर विभाग — क़ानून के अनुसार रिटर्न दाखिल करते समय।',
        'आपका डेटा कभी बेचा नहीं जाता और विज्ञापन में इस्तेमाल नहीं होता।'
      ] },
      { title: 'कितने समय तक', points: [
        'जब तक {client} और {firm} के बीच काम (एंगेजमेंट) चल रहा है।',
        'उसके बाद केवल उतने समय तक, जितना कर क़ानून व्यावसायिक रिकॉर्ड रखने के लिए कहते हैं (जैसे GST क़ानून में वार्षिक रिटर्न की नियत तारीख से 72 महीने), फिर हटा दिया जाता है।',
        'DPDP नियमों के अनुसार सुरक्षा लॉग कम से कम एक वर्ष रखे जाते हैं।'
      ] },
      { title: 'आपके अधिकार और उनका उपयोग', points: [
        'अपने व्यक्तिगत डेटा का सारांश माँगें, उसे सुधारें या अपडेट करें, हटाने को कहें (क़ानूनन ज़रूरी रिकॉर्ड को छोड़कर), शिकायत करें, या अपनी ओर से किसी को नामित करें।',
        'ऐप में “गोपनीयता और सहमति” का उपयोग करें, या {contact} से संपर्क करें। हम अधिकतम 90 दिनों में जवाब देते हैं।',
        'संतुष्ट न हों तो आप भारतीय डेटा संरक्षण बोर्ड (Data Protection Board of India) में शिकायत कर सकते हैं।'
      ] },
      { title: 'सहमति वापस लेना', points: [
        'आप कभी भी “गोपनीयता और सहमति” से सहमति वापस ले सकते हैं — एक टैप, उतना ही आसान जितना सहमति देना।',
        'वापसी के बाद सहमति के आधार पर आपके डेटा का आगे उपयोग रुक जाता है; पहले हुआ काम प्रभावित नहीं होता। क़ानूनन ज़रूरी रिकॉर्ड फिर भी रखे जाते हैं।',
        'सहमति के बिना ऐप इस्तेमाल नहीं किया जा सकता। आपकी सहमति एंगेजमेंट ख़त्म होने तक मान्य रहती है, जब तक आप पहले वापस न लें।'
      ] }
    ]
  }
};

/** Client company's data-processing terms — accepted by the client admin, or recorded by the CA firm from the signed engagement letter. */
export const CLIENT_TERMS: Record<'en' | 'hi', string> = {
  en: 'On behalf of {client}, I accept the data-processing terms: {client} confirms it is entitled to share the personal data in its records (vendors, employees) for accounting and tax compliance; {firm} processes it only to provide these services, with reasonable security safeguards, until the engagement ends or this is withdrawn; records the law requires are retained.',
  hi: '{client} की ओर से मैं डेटा-प्रोसेसिंग शर्तें स्वीकार करता/करती हूँ: {client} पुष्टि करता है कि उसे अपने रिकॉर्ड का व्यक्तिगत डेटा (विक्रेता, कर्मचारी) लेखा और कर अनुपालन के लिए साझा करने का अधिकार है; {firm} इसे केवल ये सेवाएँ देने के लिए, उचित सुरक्षा उपायों के साथ, एंगेजमेंट ख़त्म होने या यह वापस लेने तक प्रोसेस करता है; क़ानूनन ज़रूरी रिकॉर्ड रखे जाते हैं।'
};

export const fillNotice = (t: string, v: { firm: string; client: string; contact: string }) =>
  t.replace(/\{firm\}/g, v.firm).replace(/\{client\}/g, v.client).replace(/\{contact\}/g, v.contact);
