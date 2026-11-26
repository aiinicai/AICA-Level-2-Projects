/* ===== RESOLVE 360 — config.js =====
   Shared settings: required CSV columns, scoring weights and the
   recommended response for each service category. */

const CONFIG = {
  // Path of the attached dataset (used when the app is served over http)
  DATA_URL: 'data/smart_city_issues.csv',

  // Columns every uploaded CSV must contain
  REQUIRED_COLUMNS: ['issue_id', 'ward', 'category', 'severity',
    'people_affected', 'estimated_loss_inr', 'days_open', 'status'],

  NUMERIC_COLUMNS: ['severity', 'people_affected', 'estimated_loss_inr', 'days_open'],
  STATUSES: ['Open', 'In Progress', 'Resolved'],

  // Columns written by "Export filtered CSV"
  EXPORT_COLUMNS: ['issue_id', 'reported_date', 'ward', 'category', 'severity',
    'people_affected', 'estimated_loss_inr', 'days_open', 'status',
    'description', 'priority_score'],

  // Priority score weights (they add up to 100) and caps
  WEIGHTS: { severity: 35, people: 25, days: 20, loss: 20 },
  CAPS:    { severity: 5, people: 2500, days: 45, loss: 85000 },

  // Risk bands
  HIGH_RISK: 70,
  MEDIUM_RISK: 45,

  // Rows shown in the priority queue
  QUEUE_LIMIT: 100
};

const ACTIONS = {
  'Water Leakage':       'Inspect pipes, isolate leak, verify metered losses and repair urgency.',
  'Waste Management':    'Review route adherence, overflow hotspots and collection staffing.',
  'Streetlight Failure': 'Inspect electrical safety and schedule lighting restoration.',
  'Road Damage':         'Conduct safety inspection, temporary hazard control and repair scheduling.',
  'Public Complaint':    'Acknowledge complaint, assign owner and track service-level response.'
};
