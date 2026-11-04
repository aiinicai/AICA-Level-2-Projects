/* Shared helpers used by the content scripts, the popup and the service worker. */
(function (g) {
  'use strict';
  const W = (g.WDRE = g.WDRE || {});

  W.VERSION = '1.3.0';

  // Arabic-Indic and Persian digits -> ASCII, so "١٠:١٥" parses like "10:15".
  W.normDigits = (s) =>
    String(s)
      .replace(/[٠-٩]/g, (c) => String(c.charCodeAt(0) - 0x660))
      .replace(/[۰-۹]/g, (c) => String(c.charCodeAt(0) - 0x6f0));

  // Invisible direction marks that WhatsApp inserts around dates and names.
  W.stripMarks = (s) => String(s).replace(/[‎‏؜‪-‮⁦-⁩﻿]/g, '');

  // Normalised text for matching (never for display).
  W.norm = (s) =>
    W.stripMarks(W.normDigits(s == null ? '' : s))
      .replace(/،/g, ',')
      .replace(/[   ]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

  W.escapeHtml = (s) =>
    String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  W.pad2 = (n) => String(n).padStart(2, '0');
  W.sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  W.uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

  const RESERVED = /^(con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])$/i;

  // One Windows-safe path segment (folder or file base name).
  W.cleanSegment = function (s, maxLen = 80, fallback = 'Untitled') {
    let t = W.stripMarks(String(s == null ? '' : s).normalize('NFC'));
    t = t
      .replace(/[\u0000-\u001f\u007f]/g, ' ')
      .replace(/[<>:"/\\|?*]/g, '_')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/^[.\s]+/, '')
      .replace(/[.\s]+$/, '');
    const chars = Array.from(t);
    if (chars.length > maxLen) t = chars.slice(0, maxLen).join('').replace(/[.\s]+$/, '');
    if (!t) t = fallback;
    if (RESERVED.test(t.split('.')[0])) t = '_' + t;
    return t;
  };

  W.splitExt = function (name) {
    const m = /^(.*[^.\s])(\.[A-Za-z0-9]{1,10})$/.exec(String(name || ''));
    return m ? [m[1], m[2]] : [String(name || ''), ''];
  };

  W.cleanFileName = function (name, maxBase = 100, fallback = 'file') {
    const [b, e] = W.splitExt(W.stripMarks(String(name || '')).trim());
    return W.cleanSegment(b, maxBase, fallback) + e;
  };

  W.basename = (p) => String(p || '').split(/[\\/]/).pop();
  W.encodeRelPath = (rel) => String(rel).split('/').map(encodeURIComponent).join('/');

  W.MIME_EXT = {
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'image/gif': '.gif',
    'image/heic': '.heic',
    'video/mp4': '.mp4',
    'video/3gpp': '.3gp',
    'video/quicktime': '.mov',
    'video/webm': '.webm',
    'audio/ogg': '.ogg',
    'audio/opus': '.opus',
    'audio/mpeg': '.mp3',
    'audio/mp4': '.m4a',
    'audio/aac': '.aac',
    'audio/amr': '.amr',
    'audio/wav': '.wav',
    'application/pdf': '.pdf',
    'application/zip': '.zip',
    'application/msword': '.doc',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'text/plain': '.txt',
    'text/csv': '.csv',
  };
  W.extForMime = (mime) => W.MIME_EXT[String(mime || '').split(';')[0].trim().toLowerCase()] || '';

  W.KIND_LABEL = {
    image: 'Photo',
    video: 'Video',
    gif: 'GIF',
    voice: 'Voice note',
    audio: 'Audio',
    sticker: 'Sticker',
    document: 'Document',
    unknown: 'Attachment',
  };
  W.KIND_DEFAULT_EXT = { image: '.jpg', video: '.mp4', gif: '.mp4', voice: '.ogg', audio: '.mp3', sticker: '.webp' };

  // File-type groups used by the attachment filters.
  W.FILE_TYPES = [
    { key: 'image', label: 'Photos' },
    { key: 'video', label: 'Videos & GIFs' },
    { key: 'audio', label: 'Voice notes & audio' },
    { key: 'sticker', label: 'Stickers' },
    { key: 'pdf', label: 'PDF' },
    { key: 'word', label: 'Word' },
    { key: 'excel', label: 'Excel & CSV' },
    { key: 'ppt', label: 'PowerPoint' },
    { key: 'archive', label: 'ZIP & archives' },
    { key: 'other', label: 'Other files' },
  ];

  W.fileTypeKey = function (kind, name) {
    if (kind === 'image') return 'image';
    if (kind === 'video' || kind === 'gif') return 'video';
    if (kind === 'voice' || kind === 'audio') return 'audio';
    if (kind === 'sticker') return 'sticker';
    const ext = (W.splitExt(name || '')[1] || '').toLowerCase();
    if (ext === '.pdf') return 'pdf';
    if (/^\.(docx?|docm|rtf|odt|pages)$/.test(ext)) return 'word';
    if (/^\.(xlsx?|xlsm|xlsb|csv|ods|numbers)$/.test(ext)) return 'excel';
    if (/^\.(pptx?|ppsx?|odp|key)$/.test(ext)) return 'ppt';
    if (/^\.(zip|rar|7z|tar|gz|tgz)$/.test(ext)) return 'archive';
    // Pictures, videos and audio sent "as a document" keep their natural group.
    if (/^\.(jpe?g|png|gif|webp|heic|bmp|tiff?)$/.test(ext)) return 'image';
    if (/^\.(mp4|mov|3gp|avi|mkv|webm)$/.test(ext)) return 'video';
    if (/^\.(mp3|m4a|ogg|opus|wav|aac|amr)$/.test(ext)) return 'audio';
    return 'other';
  };

  W.fileTypeLabel = (key) => (W.FILE_TYPES.find((t) => t.key === key) || { label: 'Other files' }).label;

  // filter: { direction: 'all' | 'received' | 'sent', types: null (all) | [keys] }
  W.isDefaultFilter = (f) => !f || ((!f.direction || f.direction === 'all') && !f.types);
  W.matchesFilter = function (att, f) {
    if (W.isDefaultFilter(f)) return true;
    if (f.direction === 'received' && att.fromMe) return false;
    if (f.direction === 'sent' && !att.fromMe) return false;
    if (Array.isArray(f.types) && !f.types.includes(att.typeKey)) return false;
    return true;
  };
  W.describeFilter = function (f) {
    if (W.isDefaultFilter(f)) return 'all attachments';
    const parts = [];
    if (f.direction === 'received') parts.push('received only');
    if (f.direction === 'sent') parts.push('sent only');
    if (Array.isArray(f.types)) parts.push(f.types.length ? f.types.map(W.fileTypeLabel).join(', ') : 'no file types');
    return parts.join('; ');
  };
})(globalThis);
