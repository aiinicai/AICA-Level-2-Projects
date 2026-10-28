// Fictional UAE-style companies and people. Any resemblance to real entities is coincidental.

export const OUR_COMPANY = 'Desert Pearl Trading LLC';
export const OUR_ADDRESS = 'Office 1204, Al Saqr Business Tower, Sheikh Zayed Road, Dubai, UAE';
export const OUR_TRN = '100384572900003';

export const CUSTOMERS = [
  'Al Noor Trading LLC',
  'Bin Hamdan Building Materials LLC',
  'Sahara Star Foodstuff Trading',
  'Blue Lagoon Marine Services LLC',
  'Falcon Crest Logistics FZE',
  'Palm Horizon Contracting LLC',
  'Jumeirah Fine Interiors LLC',
  'Zabeel Medical Supplies Trading',
  'Hatta Fresh Dairy LLC',
  'Al Qusais Hardware Trading',
  'Corniche Hospitality Services',
  'Silver Dune Events LLC',
  'Al Barsha Facility Management',
  'Marina Bay Yacht Supplies FZCO',
  'Oud Metha Pharmacy Group',
  'Golden Sands Cafeteria LLC',
  'Nad Al Sheba Equestrian Supplies',
  'Al Khawaneej Landscaping LLC',
];

export const SUPPLIERS = [
  'Gulf Supplies LLC',
  'Oasis Office Solutions LLC',
  'Al Wasl Technical Services',
  'Creek Side Electricals LLC',
  'Al Majaz Packaging Industries',
  'Mirdif Auto Spares Trading',
  'Rashidiya Steel Fabrication LLC',
  'Emirates Pallet & Crate Factory',
  'Sharjah Print House LLC',
  'Al Quoz Industrial Chemicals',
  'Desert Rose Cleaning Services',
  'Jebel Ali Freight Forwarders',
  'Ras Al Khor Timber Trading',
  'Al Rigga IT Solutions FZ LLC',
  'Karama Uniforms & Workwear',
  'Fujairah Stone & Marble Co',
];

export const POS_MERCHANTS = [
  'PETRO STAR SERVICE STN 214',
  'DUNE FUEL 1187 AL QUOZ',
  'SAND CITY HYPERMARKET',
  'GREEN BASKET HYPERMARKET QUSAIS',
  'TOOLMART HARDWARE FESTIVAL',
  'PAPERLINE STATIONERY AL BARSHA',
  'TOLL GATE TOP UP',
  'CITY PARKING ONLINE',
  'SOUQ CART ONLINE',
  'DESERT COURIER EXPRESS',
];

export const FIRST_MALE = [
  'Mohammed', 'Ahmed', 'Abdullah', 'Omar', 'Khalid', 'Yousef', 'Hassan', 'Ali', 'Rashid', 'Saeed',
  'Faisal', 'Tariq', 'Imran', 'Rahul', 'Suresh', 'Anil', 'Vijay', 'Ravi', 'Arjun', 'Sanjay',
  'Jose', 'Mark', 'John Paul', 'Ramon', 'Nikhil', 'Shahid', 'Bilal', 'Kamran', 'Waleed', 'Hamza',
  'Ibrahim', 'Mustafa', 'Karim', 'Nabil', 'Samir', 'Fahad', 'Majid', 'Zubair', 'Arif', 'Pradeep',
];
export const FIRST_FEMALE = [
  'Fatima', 'Aisha', 'Mariam', 'Noura', 'Hessa', 'Sara', 'Layla', 'Reem', 'Huda', 'Amna',
  'Priya', 'Anjali', 'Deepa', 'Kavitha', 'Maria', 'Grace', 'Joy', 'Cristina', 'Rania', 'Dina',
];
export const MIDDLE = [
  'Abdul', 'Rafi', 'Noor', 'Kumar', 'Salem', 'Jamal', 'Ahmad', 'Rahman', 'Hamid', 'Latif',
  'Santos', 'Reyes', 'Thomas', 'George', 'Nair', 'Iqbal', 'Aziz', 'Karim', 'Hussain', 'Sultan',
];
export const LAST = [
  'Al Hashimi', 'Al Mansouri', 'Al Suwaidi', 'Al Falasi', 'Al Marri', 'Khan', 'Qureshi', 'Siddiqui',
  'Menon', 'Pillai', 'Sharma', 'Patel', 'Reddy', 'Fernandes', 'D\'Souza', 'Dela Cruz', 'Bautista',
  'Mendoza', 'Haddad', 'Nasser', 'Saleh', 'Farouk', 'Mahmoud', 'Abdel Aziz', 'Rizvi', 'Chaudhry',
  'Varghese', 'Mathew', 'Kurian', 'Iyer', 'Ansari', 'Sheikh', 'Bhatt', 'Gonzales', 'Ramos', 'Aquino',
];

export const DEPARTMENTS = ['Sales', 'Warehouse', 'Logistics', 'Finance', 'Procurement', 'Admin & HR', 'IT', 'Customer Service', 'Showroom'];

// UAE bank codes (3 digits inside the IBAN) with display names used in the WPS register.
export const UAE_BANKS = [
  { code: '026', name: 'Emirates NBD' },
  { code: '030', name: 'ADCB' },
  { code: '035', name: 'First Abu Dhabi Bank' },
  { code: '033', name: 'Mashreq' },
  { code: '024', name: 'Dubai Islamic Bank' },
  { code: '050', name: 'ADIB' },
  { code: '040', name: 'RAKBANK' },
  { code: '023', name: 'Commercial Bank of Dubai' },
];

/** Build a correctly shaped AE IBAN (AEkk BBB AAAAAAAAAAAAAAAA) with valid mod-97 check digits. */
export function makeIban(bankCode, account16) {
  const bban = bankCode + account16;
  const rearranged = bban + '1014' + '00'; // A=10, E=14, then '00'
  let rem = 0;
  for (const ch of rearranged) rem = (rem * 10 + Number(ch)) % 97;
  const check = String(98 - rem).padStart(2, '0');
  return `AE${check}${bban}`;
}
export function ibanIsValid(iban) {
  if (!/^AE\d{21}$/.test(iban)) return false;
  const s = iban.slice(4) + '1014' + iban.slice(2, 4);
  let rem = 0;
  for (const ch of s) rem = (rem * 10 + Number(ch)) % 97;
  return rem === 1;
}
