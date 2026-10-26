import { NormalizedAlert } from '../types';
import { inr, longD } from './calculations';

export function formatIcsDate(dateStr: string): string {
  // Returns YYYYMMDD for all-day events
  return dateStr.replace(/-/g, '');
}

export function generateIcsForAlert(alert: NormalizedAlert): string {
  const d = alert.due; // YYYY-MM-DD
  const dtStart = formatIcsDate(d);
  // All-day end date is the next day in iCal spec
  const nextDate = new Date(new Date(d).getTime() + 86400000).toISOString().slice(0, 10);
  const dtEnd = formatIcsDate(nextDate);

  const summary = `Paisa Pal: ${alert.label} - ${alert.name}${
    alert.amount > 0 ? ` (${inr(alert.amount)})` : ''
  }`;

  const descParts: string[] = [
    `Paisa Pal Reminder: ${alert.label}`,
    `Item: ${alert.name}`,
    alert.who ? `Holder / Person: ${alert.who}` : '',
    alert.sub ? `Provider / Bank: ${alert.sub}` : '',
    alert.amount > 0 ? `Amount: ${inr(alert.amount)}` : '',
    `Due Date: ${longD(alert.due)}`,
  ].filter(Boolean);

  const description = descParts.join('\\n');
  const uid = `paisapal-${alert.row.id}-${dtStart}@local`;

  // Alarms: 7 days before, 1 day before, and 0 days (morning)
  const icsLines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Paisa Pal//Personal Finance App//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${uid}`,
    `DTSTAMP:${formatIcsDate(new Date().toISOString().slice(0, 10))}T090000Z`,
    `DTSTART;VALUE=DATE:${dtStart}`,
    `DTEND;VALUE=DATE:${dtEnd}`,
    `SUMMARY:${summary}`,
    `DESCRIPTION:${description}`,
    'STATUS:CONFIRMED',
    // 7 days before alarm
    'BEGIN:VALARM',
    'TRIGGER:-P7D',
    'ACTION:DISPLAY',
    `DESCRIPTION:Reminder: ${summary} in 7 days`,
    'END:VALARM',
    // 1 day before alarm
    'BEGIN:VALARM',
    'TRIGGER:-P1D',
    'ACTION:DISPLAY',
    `DESCRIPTION:Reminder: ${summary} tomorrow!`,
    'END:VALARM',
    // On the day morning alarm
    'BEGIN:VALARM',
    'TRIGGER:PT9H',
    'ACTION:DISPLAY',
    `DESCRIPTION:Due Today: ${summary}`,
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ];

  return icsLines.join('\r\n');
}

export function downloadCalendarEvent(alert: NormalizedAlert) {
  const ics = generateIcsForAlert(alert);
  const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeName = alert.name.toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, 30);
  a.download = `reminder-${safeName}-${alert.due}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function getGoogleCalendarUrl(alert: NormalizedAlert): string {
  const dtStart = formatIcsDate(alert.due);
  const nextDate = new Date(new Date(alert.due).getTime() + 86400000).toISOString().slice(0, 10);
  const dtEnd = formatIcsDate(nextDate);

  const title = encodeURIComponent(
    `Paisa Pal: ${alert.label} - ${alert.name}${alert.amount > 0 ? ` (${inr(alert.amount)})` : ''}`
  );

  const details = encodeURIComponent(
    [
      `Reminder from Paisa Pal:`,
      `Item: ${alert.name}`,
      alert.who ? `Holder: ${alert.who}` : '',
      alert.sub ? `Provider / Bank: ${alert.sub}` : '',
      alert.amount > 0 ? `Amount: ${inr(alert.amount)}` : '',
      `Due Date: ${longD(alert.due)}`,
    ]
      .filter(Boolean)
      .join('\n')
  );

  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&dates=${dtStart}/${dtEnd}&details=${details}`;
}

export function generateAllIcs(alerts: NormalizedAlert[]): string {
  const events = alerts.map((a) => {
    const dtStart = formatIcsDate(a.due);
    const nextDate = new Date(new Date(a.due).getTime() + 86400000).toISOString().slice(0, 10);
    const dtEnd = formatIcsDate(nextDate);
    const summary = `Paisa Pal: ${a.label} - ${a.name}${a.amount > 0 ? ` (${inr(a.amount)})` : ''}`;
    const uid = `paisapal-${a.row.id}-${dtStart}@local`;
    return [
      'BEGIN:VEVENT',
      `UID:${uid}`,
      `DTSTART;VALUE=DATE:${dtStart}`,
      `DTEND;VALUE=DATE:${dtEnd}`,
      `SUMMARY:${summary}`,
      'STATUS:CONFIRMED',
      'BEGIN:VALARM',
      'TRIGGER:-P1D',
      'ACTION:DISPLAY',
      `DESCRIPTION:Reminder: ${summary} tomorrow!`,
      'END:VALARM',
      'END:VEVENT',
    ].join('\r\n');
  });

  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Paisa Pal//Personal Finance App//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    ...events,
    'END:VCALENDAR',
  ].join('\r\n');
}
