/*
 * Saathi core engine: pure calculations, no network, no API keys.
 * Used by index.html in the browser, and by the Node tests in /tests.
 *
 *  - Sun longitude: Meeus low-precision solar theory (~0.01°)
 *  - Moon longitude: Meeus ch. 47 main periodic terms (~0.05°)
 *  - Sidereal (Vedic) positions: Lahiri ayanamsa, linear approximation around J2000
 *  - Sunrise/sunset: NOAA solar algorithm (~1–2 min)
 *  - Panchang: vara, tithi and nakshatra at local sunrise; Rahu Kaal and Abhijit from real day length
 *  - Numerology: Life Path (keeps 11/22/33), Moolank, Bhagyank, Lo Shu grid and planes
 *  - Signature strokes: baseline angle, slant, size, underline (measured from what the user draws)
 *  - TIPI: Ten-Item Personality Inventory scoring (Gosling, Rentfrow & Swann, 2003)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SaathiCore = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const RAD = Math.PI / 180;
  const norm = (x) => ((x % 360) + 360) % 360;

  const SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
  const ELEMENTS = { Aries: 'Fire', Leo: 'Fire', Sagittarius: 'Fire', Taurus: 'Earth', Virgo: 'Earth', Capricorn: 'Earth', Gemini: 'Air', Libra: 'Air', Aquarius: 'Air', Cancer: 'Water', Scorpio: 'Water', Pisces: 'Water' };
  const NAKSHATRAS = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashirsha', 'Ardra', 'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'];
  const TITHIS = ['Pratipada', 'Dwitiya', 'Tritiya', 'Chaturthi', 'Panchami', 'Shashthi', 'Saptami', 'Ashtami', 'Navami', 'Dashami', 'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi'];

  // Weekday lords (Sun..Sat), traditional colours and numbers, Rahu Kaal segment (1–8 of daylight).
  const VARAS = [
    { day: 'Sunday', vedic: 'Ravivar', lord: 'Surya (Sun)', colour: 'Gold / Amber', hex: '#F5C542', number: 1, rahu: 8 },
    { day: 'Monday', vedic: 'Somvar', lord: 'Chandra (Moon)', colour: 'Pearl White', hex: '#E2E8F0', number: 2, rahu: 2 },
    { day: 'Tuesday', vedic: 'Mangalvar', lord: 'Mangal (Mars)', colour: 'Coral Red', hex: '#FB7185', number: 9, rahu: 7 },
    { day: 'Wednesday', vedic: 'Budhvar', lord: 'Budh (Mercury)', colour: 'Emerald Green', hex: '#34D399', number: 5, rahu: 5 },
    { day: 'Thursday', vedic: 'Guruvar', lord: 'Guru (Jupiter)', colour: 'Saffron Yellow', hex: '#FFB300', number: 3, rahu: 6 },
    { day: 'Friday', vedic: 'Shukravar', lord: 'Shukra (Venus)', colour: 'Pastel Rose', hex: '#F472B6', number: 6, rahu: 4 },
    { day: 'Saturday', vedic: 'Shanivar', lord: 'Shani (Saturn)', colour: 'Midnight Blue', hex: '#6366F1', number: 8, rahu: 3 },
  ];

  const CITIES = [
    { id: 'abu-dhabi', name: 'Abu Dhabi', lat: 24.4539, lon: 54.3773, tz: 'Asia/Dubai' },
    { id: 'dubai', name: 'Dubai', lat: 25.2048, lon: 55.2708, tz: 'Asia/Dubai' },
    { id: 'sharjah', name: 'Sharjah', lat: 25.3463, lon: 55.4209, tz: 'Asia/Dubai' },
    { id: 'al-ain', name: 'Al Ain', lat: 24.2075, lon: 55.7447, tz: 'Asia/Dubai' },
    { id: 'muscat', name: 'Muscat', lat: 23.588, lon: 58.3829, tz: 'Asia/Muscat' },
    { id: 'doha', name: 'Doha', lat: 25.2854, lon: 51.531, tz: 'Asia/Qatar' },
    { id: 'riyadh', name: 'Riyadh', lat: 24.7136, lon: 46.6753, tz: 'Asia/Riyadh' },
    { id: 'kuwait', name: 'Kuwait City', lat: 29.3759, lon: 47.9774, tz: 'Asia/Kuwait' },
    { id: 'manama', name: 'Manama', lat: 26.2285, lon: 50.586, tz: 'Asia/Bahrain' },
    { id: 'mumbai', name: 'Mumbai', lat: 19.076, lon: 72.8777, tz: 'Asia/Kolkata' },
    { id: 'delhi', name: 'New Delhi', lat: 28.6139, lon: 77.209, tz: 'Asia/Kolkata' },
    { id: 'bengaluru', name: 'Bengaluru', lat: 12.9716, lon: 77.5946, tz: 'Asia/Kolkata' },
    { id: 'chennai', name: 'Chennai', lat: 13.0827, lon: 80.2707, tz: 'Asia/Kolkata' },
    { id: 'kolkata', name: 'Kolkata', lat: 22.5726, lon: 88.3639, tz: 'Asia/Kolkata' },
    { id: 'hyderabad', name: 'Hyderabad', lat: 17.385, lon: 78.4867, tz: 'Asia/Kolkata' },
    { id: 'pune', name: 'Pune', lat: 18.5204, lon: 73.8567, tz: 'Asia/Kolkata' },
    { id: 'ahmedabad', name: 'Ahmedabad', lat: 23.0225, lon: 72.5714, tz: 'Asia/Kolkata' },
    { id: 'jaipur', name: 'Jaipur', lat: 26.9124, lon: 75.7873, tz: 'Asia/Kolkata' },
    { id: 'lucknow', name: 'Lucknow', lat: 26.8467, lon: 80.9462, tz: 'Asia/Kolkata' },
    { id: 'kochi', name: 'Kochi', lat: 9.9312, lon: 76.2673, tz: 'Asia/Kolkata' },
    { id: 'karachi', name: 'Karachi', lat: 24.8607, lon: 67.0011, tz: 'Asia/Karachi' },
    { id: 'dhaka', name: 'Dhaka', lat: 23.8103, lon: 90.4125, tz: 'Asia/Dhaka' },
    { id: 'colombo', name: 'Colombo', lat: 6.9271, lon: 79.8612, tz: 'Asia/Colombo' },
    { id: 'kathmandu', name: 'Kathmandu', lat: 27.7172, lon: 85.324, tz: 'Asia/Kathmandu' },
    { id: 'singapore', name: 'Singapore', lat: 1.3521, lon: 103.8198, tz: 'Asia/Singapore' },
    { id: 'london', name: 'London', lat: 51.5074, lon: -0.1278, tz: 'Europe/London' },
    { id: 'new-york', name: 'New York', lat: 40.7128, lon: -74.006, tz: 'America/New_York' },
    { id: 'toronto', name: 'Toronto', lat: 43.6532, lon: -79.3832, tz: 'America/Toronto' },
    { id: 'sydney', name: 'Sydney', lat: -33.8688, lon: 151.2093, tz: 'Australia/Sydney' },
  ];
  const cityById = (id) => CITIES.find((c) => c.id === id) || CITIES[0];

  /* ---------------------------- time helpers ---------------------------- */

  const julianDay = (date) => date.getTime() / 86400000 + 2440587.5;
  const centuries = (jd) => (jd - 2451545.0) / 36525;

  /** Offset (minutes) of a time zone from UTC at a given instant. */
  function tzOffsetMinutes(date, tz) {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).formatToParts(date);
    const g = (t) => Number(parts.find((p) => p.type === t).value);
    const asUtc = Date.UTC(g('year'), g('month') - 1, g('day'), g('hour'), g('minute'), g('second'));
    return Math.round((asUtc - date.getTime()) / 60000);
  }

  /** Local calendar date (YYYY-MM-DD) of an instant in a time zone. */
  function localDateKey(date, tz) {
    const off = tzOffsetMinutes(date, tz);
    return new Date(date.getTime() + off * 60000).toISOString().slice(0, 10);
  }

  /** UTC instant for local wall-clock time in a time zone. */
  function localToUtc(dateKey, hh, mm, tz) {
    const [y, m, d] = dateKey.split('-').map(Number);
    const guess = Date.UTC(y, m - 1, d, hh, mm);
    let off = tzOffsetMinutes(new Date(guess), tz);
    let t = guess - off * 60000;
    off = tzOffsetMinutes(new Date(t), tz);
    return new Date(guess - off * 60000);
  }

  function fmtTime(date, tz) {
    return new Intl.DateTimeFormat('en-GB', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: tz }).format(date).replace(/ | /g, ' ');
  }

  /* --------------------------- sun and moon --------------------------- */

  /** Apparent geocentric ecliptic longitude of the Sun, degrees (tropical). */
  function sunLongitude(date) {
    const T = centuries(julianDay(date));
    const L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T;
    const M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T;
    const C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * Math.sin(M * RAD) + (0.019993 - 0.000101 * T) * Math.sin(2 * M * RAD) + 0.000289 * Math.sin(3 * M * RAD);
    const omega = 125.04 - 1934.136 * T;
    return norm(L0 + C - 0.00569 - 0.00478 * Math.sin(omega * RAD));
  }

  // Meeus, Astronomical Algorithms, Table 47.A (largest terms): [D, M, M', F, Σl (1e-6 deg)]
  const MOON_TERMS = [
    [0, 0, 1, 0, 6288774], [2, 0, -1, 0, 1274027], [2, 0, 0, 0, 658314], [0, 0, 2, 0, 213618],
    [0, 1, 0, 0, -185116], [0, 0, 0, 2, -114332], [2, 0, -2, 0, 58793], [2, -1, -1, 0, 57066],
    [2, 0, 1, 0, 53322], [2, -1, 0, 0, 45758], [0, 1, -1, 0, -40923], [1, 0, 0, 0, -34720],
    [0, 1, 1, 0, -30383], [2, 0, 0, -2, 15327], [0, 0, 1, 2, -12528], [0, 0, 1, -2, 10980],
    [4, 0, -1, 0, 10675], [0, 0, 3, 0, 10034], [4, 0, -2, 0, 8548], [2, 1, -1, 0, -7888],
    [2, 1, 0, 0, -6766], [1, 0, -1, 0, -5163], [1, 1, 0, 0, 4987], [2, -1, 1, 0, 4036],
    [2, 0, 2, 0, 3994], [4, 0, 0, 0, 3861], [2, 0, -3, 0, 3665], [0, 1, -2, 0, -2689],
    [2, 0, -1, 2, -2602], [2, -1, -2, 0, 2390], [1, 0, 1, 0, -2348], [2, -2, 0, 0, 2236],
    [0, 1, 2, 0, -2120], [0, 2, 0, 0, -2069], [2, -2, -1, 0, 2048], [2, 0, 1, -2, -1773],
    [2, 0, 0, 2, -1595], [4, -1, -1, 0, 1215], [0, 0, 2, 2, -1110], [3, 0, -1, 0, -892],
    [2, 1, 1, 0, -810], [4, -1, -2, 0, 759], [0, 2, -1, 0, -713], [2, 2, -1, 0, -700],
    [2, 1, -2, 0, 691], [2, -1, 0, -2, 596], [4, 0, 1, 0, 549], [0, 0, 4, 0, 537],
    [4, -1, 0, 0, 520], [1, 0, -2, 0, -487],
  ];

  /** Geocentric ecliptic longitude of the Moon, degrees (tropical). */
  function moonLongitude(date) {
    const T = centuries(julianDay(date));
    const Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T;
    const D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T;
    const M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T * T;
    const Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T * T;
    const F = 93.272095 + 483202.0175233 * T - 0.0036539 * T * T;
    const E = 1 - 0.002516 * T - 0.0000074 * T * T;
    let sum = 0;
    for (const [d, m, mp, f, l] of MOON_TERMS) {
      const e = Math.abs(m) === 1 ? E : Math.abs(m) === 2 ? E * E : 1;
      sum += l * e * Math.sin((d * D + m * M + mp * Mp + f * F) * RAD);
    }
    const A1 = 119.75 + 131.849 * T;
    const A2 = 53.09 + 479264.29 * T;
    sum += 3958 * Math.sin(A1 * RAD) + 1962 * Math.sin((Lp - F) * RAD) + 318 * Math.sin(A2 * RAD);
    const omega = 125.04452 - 1934.136261 * T;
    const nutation = -0.004778 * Math.sin(omega * RAD); // main nutation term, degrees
    return norm(Lp + sum / 1e6 + nutation);
  }

  /** Lahiri ayanamsa, degrees (23.853° at J2000 + 50.2788″ per year). */
  function lahiriAyanamsa(date) {
    const years = (date.getTime() - Date.UTC(2000, 0, 1, 12)) / (365.25 * 86400000);
    return 23.853 + (50.2788 / 3600) * years;
  }

  const signOf = (lon) => SIGNS[Math.floor(norm(lon) / 30)];

  function moonPhaseName(date) {
    const p = norm(moonLongitude(date) - sunLongitude(date));
    if (p < 11.25 || p >= 348.75) return 'New Moon';
    if (p < 78.75) return 'Waxing Crescent';
    if (p < 101.25) return 'First Quarter';
    if (p < 168.75) return 'Waxing Gibbous';
    if (p < 191.25) return 'Full Moon';
    if (p < 258.75) return 'Waning Gibbous';
    if (p < 281.25) return 'Last Quarter';
    return 'Waning Crescent';
  }

  /* ------------------------------ sunrise ------------------------------ */

  /** NOAA sunrise/sunset for the local date in a city. Returns UTC Date objects or null (polar day/night). */
  function sunTimes(dateKey, city) {
    const noonUtc = localToUtc(dateKey, 12, 0, city.tz);
    const calc = (rising) => {
      let t = noonUtc;
      for (let i = 0; i < 3; i++) {
        const T = centuries(julianDay(t));
        const L0 = norm(280.46646 + T * (36000.76983 + T * 0.0003032));
        const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
        const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
        const C = Math.sin(M * RAD) * (1.914602 - T * (0.004817 + 0.000014 * T)) + Math.sin(2 * M * RAD) * (0.019993 - 0.000101 * T) + Math.sin(3 * M * RAD) * 0.000289;
        const omega = 125.04 - 1934.136 * T;
        const lambda = L0 + C - 0.00569 - 0.00478 * Math.sin(omega * RAD);
        const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60;
        const eps = eps0 + 0.00256 * Math.cos(omega * RAD);
        const decl = Math.asin(Math.sin(eps * RAD) * Math.sin(lambda * RAD));
        const y = Math.tan((eps / 2) * RAD) ** 2;
        const eqTime = 4 / RAD * (y * Math.sin(2 * L0 * RAD) - 2 * e * Math.sin(M * RAD) + 4 * e * y * Math.sin(M * RAD) * Math.cos(2 * L0 * RAD) - 0.5 * y * y * Math.sin(4 * L0 * RAD) - 1.25 * e * e * Math.sin(2 * M * RAD));
        const cosH = (Math.cos(90.833 * RAD) - Math.sin(city.lat * RAD) * Math.sin(decl)) / (Math.cos(city.lat * RAD) * Math.cos(decl));
        if (cosH > 1 || cosH < -1) return null;
        const H = Math.acos(cosH) / RAD;
        const [y0, m0, d0] = dateKey.split('-').map(Number);
        const minutesUtc = 720 - 4 * (city.lon + (rising ? H : -H)) - eqTime;
        t = new Date(Date.UTC(y0, m0 - 1, d0) + minutesUtc * 60000);
      }
      return t;
    };
    const sunrise = calc(true);
    const sunset = calc(false);
    return sunrise && sunset ? { sunrise, sunset } : null;
  }

  /* ------------------------------ panchang ------------------------------ */

  function nakshatraAt(date) {
    const sid = norm(moonLongitude(date) - lahiriAyanamsa(date));
    const i = Math.floor(sid / (360 / 27));
    const pada = Math.floor((sid % (360 / 27)) / (360 / 108)) + 1;
    return { index: i, name: NAKSHATRAS[i], pada };
  }

  function tithiAt(date) {
    const elong = norm(moonLongitude(date) - sunLongitude(date));
    const n = Math.floor(elong / 12) + 1;
    const paksha = n <= 15 ? 'Shukla' : 'Krishna';
    const k = n <= 15 ? n : n - 15;
    const name = n === 15 ? 'Purnima' : n === 30 ? 'Amavasya' : TITHIS[k - 1];
    return { number: n, paksha, name, label: `${paksha} ${name}` };
  }

  /* ----------------------------- numerology ----------------------------- */

  const digitSum = (n) => String(n).split('').reduce((a, c) => a + Number(c), 0);
  function reduce(n, keepMaster) {
    let x = Math.abs(n);
    while (x > 9 && !(keepMaster && (x === 11 || x === 22 || x === 33))) x = digitSum(x);
    return x;
  }

  /** Life Path: reduce month, day and year separately, add, then reduce (keeps 11/22/33). */
  function lifePath(birthKey) {
    const [y, m, d] = birthKey.split('-').map(Number);
    const total = reduce(m, true) + reduce(d, true) + reduce(y, true);
    return { compound: total, value: reduce(total, true) };
  }
  const moolank = (birthKey) => reduce(Number(birthKey.split('-')[2]), false);
  function bhagyank(birthKey) {
    const total = digitSum(birthKey.replace(/-/g, ''));
    return { compound: total, value: reduce(total, false) };
  }
  /** Personal day number (personal year + month + day). */
  function personalDay(birthKey, dayKey) {
    const [, bm, bd] = birthKey.split('-').map(Number);
    const [cy, cm, cd] = dayKey.split('-').map(Number);
    const year = reduce(reduce(bm) + reduce(bd) + reduce(cy));
    const month = reduce(year + reduce(cm));
    return reduce(month + reduce(cd)) || 9;
  }
  const universalDay = (dayKey) => reduce(digitSum(dayKey.replace(/-/g, ''))) || 9;

  const LOSHU_ORDER = [4, 9, 2, 3, 5, 7, 8, 1, 6];
  const LOSHU_PLANES = [
    { name: 'Mental plane', nums: [4, 9, 2], meaning: 'thinking, memory and planning' },
    { name: 'Emotional plane', nums: [3, 5, 7], meaning: 'feelings, intuition and balance' },
    { name: 'Practical plane', nums: [8, 1, 6], meaning: 'action, money sense and getting things done' },
    { name: 'Thought plane', nums: [4, 3, 8], meaning: 'ideas and strategy' },
    { name: 'Will plane', nums: [9, 5, 1], meaning: 'determination and patience' },
    { name: 'Action plane', nums: [2, 7, 6], meaning: 'turning plans into results' },
  ];
  function loShu(birthKey) {
    const counts = {};
    for (let n = 1; n <= 9; n++) counts[n] = 0;
    for (const ch of birthKey.replace(/-/g, '')) if (ch !== '0') counts[Number(ch)]++;
    const complete = LOSHU_PLANES.filter((p) => p.nums.every((n) => counts[n] > 0));
    const missing = LOSHU_ORDER.filter((n) => counts[n] === 0);
    return { counts, complete, missing };
  }

  /* ---------------------------- day card ---------------------------- */

  const REL = (from, to) => {
    const d = (SIGNS.indexOf(to) - SIGNS.indexOf(from) + 12) % 12;
    return d === 0 ? 'conjunct' : d === 4 || d === 8 ? 'trine' : d === 2 || d === 10 ? 'sextile' : d === 3 || d === 9 ? 'square' : d === 6 ? 'opposite' : 'neutral';
  };
  const REL_SCORE = { conjunct: 1, trine: 2, sextile: 1, square: -1, opposite: -1, neutral: 0 };

  const TIPS = {
    Fire: 'Move your body early and start the task you have been putting off.',
    Earth: 'Finish one practical thing, eat a proper meal and keep your desk tidy.',
    Air: 'Call a friend or share an idea; conversation lifts your energy today.',
    Water: 'Slow down, drink water often and spend time with people you love.',
  };
  const LOVED = [
    'You are not behind in life; you are blooming in the season designed for you.',
    'You bring a quiet, irreplaceable grace into every room you enter.',
    'Be proud of how gently you are showing up for yourself today.',
    'Even on slow days, you are worthy of rest and of love.',
    'The world is softer because of the care you carry.',
    'You are doing enough, you have enough, and you are deeply loved.',
    'Your smile has the power to melt heavy moments into light.',
  ];

  function hash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  /**
   * Today's sky for a city, optionally personalised with a birth date.
   * system: 'Vedic' (sidereal, Lahiri) or 'Western' (tropical).
   */
  function dayCard({ now = new Date(), cityId = 'dubai', system = 'Vedic', birthKey = null, seed = '' } = {}) {
    const city = cityById(cityId);
    const dayKey = localDateKey(now, city.tz);
    const noon = localToUtc(dayKey, 12, 0, city.tz);
    const moonTrop = moonLongitude(noon);
    const moonSid = norm(moonTrop - lahiriAyanamsa(noon));
    const moonSign = signOf(system === 'Vedic' ? moonSid : moonTrop);
    const sun = sunTimes(dayKey, city);
    const ref = sun ? sun.sunrise : localToUtc(dayKey, 6, 0, city.tz);
    const nak = nakshatraAt(ref);
    const tithi = tithiAt(ref);
    const [y, m, d] = dayKey.split('-').map(Number);
    const wd = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
    const vara = VARAS[wd];
    let rahu = null, abhijit = null;
    if (sun) {
      const len = sun.sunset - sun.sunrise;
      const seg = len / 8;
      const rs = new Date(sun.sunrise.getTime() + (vara.rahu - 1) * seg);
      rahu = { start: rs, end: new Date(rs.getTime() + seg) };
      if (wd !== 3) {
        const mu = len / 15;
        const as = new Date(sun.sunrise.getTime() + 7 * mu);
        abhijit = { start: as, end: new Date(as.getTime() + mu) };
      }
    }
    let score = null, natalSun = null, luckyNumber, luckyWhy;
    if (birthKey) {
      const bNoon = new Date(birthKey + 'T12:00:00Z');
      const bSun = sunLongitude(bNoon);
      natalSun = signOf(system === 'Vedic' ? bSun - lahiriAyanamsa(bNoon) : bSun);
      const rel = REL(natalSun, moonSign);
      score = Math.max(3, Math.min(10, Math.round(6 + REL_SCORE[rel] + (tithi.number <= 15 ? 0.5 : 0) + (wd === 0 || wd === 4 ? 0.5 : 0))));
      luckyNumber = personalDay(birthKey, dayKey);
      luckyWhy = 'Your personal day number';
    } else {
      luckyNumber = universalDay(dayKey);
      luckyWhy = 'Universal day number (add your birth date for your own)';
    }
    const element = ELEMENTS[moonSign];
    const t = (dt) => fmtTime(dt, city.tz);
    const tip = `${TIPS[element]}${rahu ? ` Avoid new starts during Rahu Kaal (${t(rahu.start)} – ${t(rahu.end)}).` : ''}`;
    return {
      dayKey, city, system, weekday: vara.day, vara,
      moonSign, moonSignVedic: signOf(moonSid), moonSignWestern: signOf(moonTrop),
      moonPhase: moonPhaseName(noon), nakshatra: nak, tithi,
      sunrise: sun ? t(sun.sunrise) : '—', sunset: sun ? t(sun.sunset) : '—',
      rahuKaal: rahu ? `${t(rahu.start)} – ${t(rahu.end)}` : '—',
      abhijit: abhijit ? `${t(abhijit.start)} – ${t(abhijit.end)}` : 'Not used on Wednesdays',
      luckyColour: vara.colour, luckyHex: vara.hex, luckyNumber, luckyWhy,
      score, natalSun, element, tip,
      lovedLine: LOVED[hash(`${seed}|${dayKey}`) % LOVED.length],
    };
  }

  /* ------------------------- signature strokes ------------------------- */

  /**
   * Measure a signature drawn on screen. strokes: [[{x,y}, ...], ...] in canvas pixels (y down).
   * Returns null when there is not enough ink to measure honestly.
   */
  function analyseSignature(strokes, canvasWidth, canvasHeight) {
    const pts = strokes.flat();
    if (pts.length < 25) return null;
    const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const width = maxX - minX, height = maxY - minY;
    if (width < 50 || height < 12) return null;

    // Underline: a long, nearly flat stroke in the lower part spanning most of the width.
    const flatLong = (s) => {
      const sx = s.map((p) => p.x), sy = s.map((p) => p.y);
      const w = Math.max(...sx) - Math.min(...sx), h = Math.max(...sy) - Math.min(...sy);
      return w > 0.6 * width && h < 0.25 * height && Math.min(...sy) > minY + 0.5 * height;
    };
    const underline = strokes.some(flatLong);
    const body = strokes.filter((s) => !flatLong(s)).flat();

    // Baseline: the bottom turning points of each stroke (where the pen touches the line),
    // fitted with a robust median-of-slopes (Theil–Sen) line so descenders don't pull it off.
    const bottoms = [];
    for (const st of strokes) {
      if (flatLong(st)) continue;
      for (let i = 0; i < st.length; i++) {
        const prev = st[i - 1], next = st[i + 1];
        const isBottom = (!prev || st[i].y >= prev.y) && (!next || st[i].y >= next.y);
        if (isBottom) bottoms.push(st[i]);
      }
    }
    const midY = minY + 0.4 * height;
    const bp = bottoms.filter((p) => p.y >= midY);
    let baselineDeg = 0;
    if (bp.length >= 3) {
      const slopes = [];
      for (let i = 0; i < bp.length; i++) for (let j = i + 1; j < bp.length; j++) {
        const dx = bp[j].x - bp[i].x;
        if (Math.abs(dx) > 8) slopes.push((bp[j].y - bp[i].y) / dx);
      }
      slopes.sort((a, b) => a - b);
      const m = slopes.length ? slopes[Math.floor(slopes.length / 2)] : 0;
      baselineDeg = -Math.atan(m) / RAD; // + = rising to the right
    }
    void body;

    // Slant: length-weighted lean of near-vertical segments (90° = upright, >90° leans right).
    let wsum = 0, asum = 0;
    for (const s of strokes) {
      for (let i = 1; i < s.length; i++) {
        const dx = s[i].x - s[i - 1].x, dy = s[i].y - s[i - 1].y;
        const len = Math.hypot(dx, dy);
        if (len < 2 || Math.abs(dy) < Math.abs(dx) * 1.2) continue;
        const lean = Math.atan2(dy > 0 ? -dx : dx, Math.abs(dy)) / RAD; // positive when the top is to the right
        asum += lean * len; wsum += len;
      }
    }
    const slantDeg = wsum ? 90 + asum / wsum : 90;
    const sizeRatio = height / canvasHeight;

    const slantClass = slantDeg < 80 ? 'left-leaning' : slantDeg <= 95 ? 'upright' : 'right-leaning';
    const baselineClass = baselineDeg > 2 ? 'rising' : baselineDeg < -2 ? 'falling' : 'level';
    const sizeClass = sizeRatio < 0.3 ? 'compact' : sizeRatio > 0.65 ? 'large' : 'medium';
    const READ = {
      slant: { 'left-leaning': 'A left lean is linked with reflection and thinking before reacting.', upright: 'An upright slant is linked with composure and steady judgement.', 'right-leaning': 'A right lean is linked with warmth and reaching out to people.' },
      baseline: { rising: 'A rising baseline is traditionally read as optimism and forward drive.', level: 'A level baseline is traditionally read as steadiness and reliability.', falling: 'A falling baseline can simply mean a tired hand; try again when rested.' },
      size: { compact: 'A compact signature is linked with focus and modesty.', medium: 'A medium size suggests a balanced public presence.', large: 'A large signature is linked with confidence and enjoying visibility.' },
    };
    return {
      slantDeg: Math.round(slantDeg), baselineDeg: Math.round(baselineDeg * 10) / 10, sizeRatio: Math.round(sizeRatio * 100) / 100,
      underline, slantClass, baselineClass, sizeClass,
      reading: [READ.slant[slantClass], READ.baseline[baselineClass], READ.size[sizeClass], underline ? 'An underline is linked with wanting your work to be noticed.' : ''].filter(Boolean),
    };
  }

  /* -------------------------------- TIPI -------------------------------- */

  const TIPI_ITEMS = [
    'Extraverted, enthusiastic', 'Critical, quarrelsome', 'Dependable, self-disciplined', 'Anxious, easily upset', 'Open to new experiences, complex',
    'Reserved, quiet', 'Sympathetic, warm', 'Disorganized, careless', 'Calm, emotionally stable', 'Conventional, uncreative',
  ];
  /** answers: 10 numbers 1–7. Returns trait means (1–7) and percentages (0–100). */
  function scoreTipi(answers) {
    if (!Array.isArray(answers) || answers.length !== 10 || answers.some((a) => !(a >= 1 && a <= 7))) return null;
    const r = (i) => 8 - answers[i];
    const a = (i) => answers[i];
    const traits = {
      Extraversion: (a(0) + r(5)) / 2,
      Agreeableness: (r(1) + a(6)) / 2,
      Conscientiousness: (a(2) + r(7)) / 2,
      'Emotional stability': (r(3) + a(8)) / 2,
      Openness: (a(4) + r(9)) / 2,
    };
    const pct = {};
    for (const k of Object.keys(traits)) pct[k] = Math.round(((traits[k] - 1) / 6) * 100);
    return { traits, pct };
  }

  /* ------------------------------ points ------------------------------ */

  const LEVELS = [
    { name: 'Spark', min: 0 }, { name: 'Glow', min: 300 }, { name: 'Shine', min: 900 }, { name: 'Radiant', min: 2000 }, { name: 'Luminous', min: 4000 },
  ];
  function levelFor(points) {
    let i = 0;
    while (i + 1 < LEVELS.length && points >= LEVELS[i + 1].min) i++;
    const next = LEVELS[i + 1];
    return { name: LEVELS[i].name, next: next ? next.min : null, progress: next ? (points - LEVELS[i].min) / (next.min - LEVELS[i].min) : 1 };
  }

  /** Streak: consecutive days (ending today or yesterday) with at least one activity. */
  function streak(activeDays, todayKey) {
    const set = new Set(activeDays);
    const prev = (k) => { const d = new Date(k + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() - 1); return d.toISOString().slice(0, 10); };
    let k = set.has(todayKey) ? todayKey : prev(todayKey);
    let n = 0;
    while (set.has(k)) { n++; k = prev(k); }
    return n;
  }

  const FORTUNES = [
    'A warm heart will unlock a doorway that intellect has been knocking on for weeks.',
    'Your body is asking for kindness today, not perfection. Listen gently.',
    'An unexpected kindness will find you before sundown.',
    'A sip of stillness will bring you more clarity than a storm of rushing.',
    'You are blooming in the season designed specifically for your soul.',
    'Trust the rhythm of your breath when the noise of the day gets too loud.',
    'Drink a tall glass of water; your energy is waiting to be refreshed.',
    'Small steps, taken daily, become a life you love.',
    'Someone is grateful for you today, even if they have not said it yet.',
    'The quietest moments often hold your greatest breakthroughs.',
    'Let today be lighter: one task at a time, one breath at a time.',
    'Your future self is already thanking you for showing up today.',
  ];
  /** One fortune per person per day; about 1 in 12 days is golden. */
  function dailyFortune(seed, dayKey) {
    const h = hash(`${seed}|${dayKey}`);
    return { text: FORTUNES[h % FORTUNES.length], golden: h % 12 === 0 };
  }

  return {
    SIGNS, NAKSHATRAS, VARAS, CITIES, TIPI_ITEMS, LOSHU_ORDER,
    cityById, localDateKey, localToUtc, tzOffsetMinutes, fmtTime,
    sunLongitude, moonLongitude, lahiriAyanamsa, signOf, moonPhaseName, sunTimes, nakshatraAt, tithiAt,
    lifePath, moolank, bhagyank, personalDay, universalDay, loShu,
    dayCard, analyseSignature, scoreTipi, levelFor, streak, dailyFortune, hash,
  };
});
