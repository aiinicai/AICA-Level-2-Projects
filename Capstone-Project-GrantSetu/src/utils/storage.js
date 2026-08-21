/**
 * LocalStorage Persistence & Backup Utilities for GrantSetu
 */
import {
  initialNgoProfile,
  initialGrants,
  initialProposals,
  initialExpenses,
  initialClosureRecords
} from './sampleData';

const KEYS = {
  PROFILE: 'grantsetu_ngo_profile_v1',
  GRANTS: 'grantsetu_grants_v1',
  PROPOSALS: 'grantsetu_proposals_v1',
  EXPENSES: 'grantsetu_expenses_v1',
  CLOSURES: 'grantsetu_closures_v1'
};

export const loadStoredData = () => {
  try {
    const profile = localStorage.getItem(KEYS.PROFILE);
    const grants = localStorage.getItem(KEYS.GRANTS);
    const proposals = localStorage.getItem(KEYS.PROPOSALS);
    const expenses = localStorage.getItem(KEYS.EXPENSES);
    const closures = localStorage.getItem(KEYS.CLOSURES);

    return {
      profile: profile ? JSON.parse(profile) : initialNgoProfile,
      grants: grants ? JSON.parse(grants) : initialGrants,
      proposals: proposals ? JSON.parse(proposals) : initialProposals,
      expenses: expenses ? JSON.parse(expenses) : initialExpenses,
      closures: closures ? JSON.parse(closures) : initialClosureRecords
    };
  } catch (e) {
    console.error('Failed to parse localStorage data:', e);
    return {
      profile: initialNgoProfile,
      grants: initialGrants,
      proposals: initialProposals,
      expenses: initialExpenses,
      closures: initialClosureRecords
    };
  }
};

export const saveStoredData = (key, data) => {
  try {
    localStorage.setItem(KEYS[key], JSON.stringify(data));
  } catch (e) {
    console.error(`Error saving data for ${key}:`, e);
  }
};

export const resetToDemoData = () => {
  try {
    localStorage.setItem(KEYS.PROFILE, JSON.stringify(initialNgoProfile));
    localStorage.setItem(KEYS.GRANTS, JSON.stringify(initialGrants));
    localStorage.setItem(KEYS.PROPOSALS, JSON.stringify(initialProposals));
    localStorage.setItem(KEYS.EXPENSES, JSON.stringify(initialExpenses));
    localStorage.setItem(KEYS.CLOSURES, JSON.stringify(initialClosureRecords));
    return {
      profile: initialNgoProfile,
      grants: initialGrants,
      proposals: initialProposals,
      expenses: initialExpenses,
      closures: initialClosureRecords
    };
  } catch (e) {
    console.error('Failed to reset demo data:', e);
    return null;
  }
};

export const exportFullBackup = (data) => {
  const backupObject = {
    app: 'GrantSetu - Indian NGO Grant Management System',
    exportDate: new Date().toISOString(),
    version: '1.0.0',
    data: data
  };
  const jsonStr = JSON.stringify(backupObject, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `GrantSetu_NGO_Backup_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
};
