/**
 * Screen copy that more than one view uses.
 *
 * Copy rules: sentence case, and never the forbidden assurance word. The tool
 * records a position assessed against stated criteria on the evidence
 * provided; it never asserts more than that.
 */

const WORDS = Object.freeze({
  notesButton: 'Note and response',
  noteHint: 'working paper — not printed in the report',
  responseHint: 'printed in the report',
  noteMark: 'note',
  responseMark: 'response',
  scopePhrase: 'this engagement',
  entityRow: 'Entity',
  roleRow: 'Assessed role',
  reportKind: 'Readiness report issued by the assessor',
  reportProse: 'The report states the position assessed against stated criteria on the evidence '
    + 'provided. It is a readiness review and makes no assertion beyond that.',
  newTitle: 'New assessment',
  entityName: 'Name of the entity',
  entityNameError: 'Enter the name of the entity being assessed.',
  assessedBy: 'Assessed by',
  roleTitle: 'Engagement role',
  roleLabel: 'Assessed role for this engagement',
  borderlineNote: 'This determination is finely balanced. It is recorded with the reasoning above and '
    + 'should be confirmed against the executed contract before the report is issued.',
  unassessedNote: (n) => (n === 1
    ? '1 control is not yet assessed; it scores nil until assessed.'
    : `${n} controls are not yet assessed; they score nil until assessed.`),
  noteLabel: 'Assessor note',
  responseLabel: 'Management response',
  ownerLabel: 'Owner',
  targetLabel: 'Target date',
});

export function words() {
  return WORDS;
}
