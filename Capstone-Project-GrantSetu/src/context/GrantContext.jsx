import React, { createContext, useContext, useState, useEffect } from 'react';
import { loadStoredData, saveStoredData, resetToDemoData, exportFullBackup } from '../utils/storage';
import { initialSubGrants } from '../utils/sampleData';

const GrantContext = createContext();

export const GrantProvider = ({ children }) => {
  const [data, setData] = useState(() => {
    const loaded = loadStoredData();
    return {
      ...loaded,
      subGrants: loaded.subGrants || initialSubGrants
    };
  });

  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedGrantId, setSelectedGrantId] = useState(null);
  const [selectedProposalId, setSelectedProposalId] = useState(null);
  const [notification, setNotification] = useState(null);

  const showToast = (text, type = 'success') => {
    setNotification({ text, type });
    setTimeout(() => {
      setNotification(null);
    }, 4500);
  };

  // Sync to local storage
  useEffect(() => { saveStoredData('PROFILE', data.profile); }, [data.profile]);
  useEffect(() => { saveStoredData('GRANTS', data.grants); }, [data.grants]);
  useEffect(() => { saveStoredData('PROPOSALS', data.proposals); }, [data.proposals]);
  useEffect(() => { saveStoredData('EXPENSES', data.expenses); }, [data.expenses]);
  useEffect(() => { saveStoredData('CLOSURES', data.closures); }, [data.closures]);
  useEffect(() => { saveStoredData('SUBGRANTS', data.subGrants); }, [data.subGrants]);

  // Profile operations
  const updateProfile = (updatedProfile) => {
    setData((prev) => ({
      ...prev,
      profile: { ...prev.profile, ...updatedProfile }
    }));
    showToast('NGO Profile & Regulatory credentials updated successfully!');
  };

  // Proposal operations
  const addProposal = (newProp) => {
    const id = `PROP-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`;
    const fullProp = {
      id,
      status: 'Draft',
      documents: newProp.documents || [],
      ...newProp
    };
    setData((prev) => ({
      ...prev,
      proposals: [fullProp, ...prev.proposals]
    }));
    showToast(`New Grant Proposal "${fullProp.title}" created!`);
    return id;
  };

  const updateProposal = (updatedProp) => {
    setData((prev) => ({
      ...prev,
      proposals: prev.proposals.map((p) => (p.id === updatedProp.id ? updatedProp : p))
    }));
    showToast(`Proposal "${updatedProp.title}" updated.`);
  };

  // Sanction a proposal -> Convert to Active Grant
  const sanctionProposalToGrant = (proposalId, sanctionDetails) => {
    const prop = data.proposals.find((p) => p.id === proposalId);
    if (!prop) return;

    const newGrantId = `GRANT-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`;
    
    const budgetBreakdown = (prop.budgetItems || []).map((item) => ({
      category: item.category,
      allocated: Number(item.cost || 0),
      spent: 0
    }));

    const newGrant = {
      id: newGrantId,
      proposalId: prop.id,
      title: prop.title,
      donorName: prop.donorName,
      fundingType: prop.fundingType,
      bankAccountType: sanctionDetails.bankAccountType || (prop.fundingType === 'FCRA Foreign' ? 'FCRA' : 'Domestic'),
      sanctionOrderNo: sanctionDetails.sanctionOrderNo || `MO/SANCTION/${Math.floor(1000 + Math.random() * 9000)}`,
      sanctionDate: sanctionDetails.sanctionDate || new Date().toISOString().slice(0, 10),
      startDate: sanctionDetails.startDate || new Date().toISOString().slice(0, 10),
      endDate: sanctionDetails.endDate || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      totalSanctionedAmount: Number(sanctionDetails.totalSanctionedAmount || prop.totalBudget || 0),
      receivedAmount: Number(sanctionDetails.firstTrancheAmount || 0),
      spentAmount: 0,
      status: 'Active',
      restrictedFund: sanctionDetails.restrictedFund !== false,
      fcraCompliant: true,
      
      tranches: [
        {
          id: 'T1',
          trancheNo: 1,
          amount: Number(sanctionDetails.firstTrancheAmount || prop.totalBudget * 0.5),
          expectedDate: sanctionDetails.startDate || new Date().toISOString().slice(0, 10),
          status: sanctionDetails.firstTrancheAmount ? 'Received' : 'Scheduled',
          receivedDate: sanctionDetails.firstTrancheAmount ? (sanctionDetails.startDate || new Date().toISOString().slice(0, 10)) : null,
          ucRequired: false,
          ucSubmitted: false
        }
      ],
      budgetBreakdown: budgetBreakdown.length > 0 ? budgetBreakdown : [
        { category: 'Program Implementation Expenses', allocated: Number(prop.totalBudget || 0) * 0.7, spent: 0 },
        { category: 'Personnel & Field Staff', allocated: Number(prop.totalBudget || 0) * 0.25, spent: 0 },
        { category: 'Administrative Overheads', allocated: Number(prop.totalBudget || 0) * 0.05, spent: 0 }
      ],
      kpis: (prop.logFrame?.outputs || []).map((output) => ({
        name: output,
        target: 100,
        achieved: 0,
        unit: 'Units'
      })),
      logFrameSummary: {
        goal: prop.logFrame?.goal || '',
        outcome: prop.logFrame?.outcome || '',
        outputs: (prop.logFrame?.outputs || []).join(', ')
      }
    };

    const updatedProposals = data.proposals.map((p) =>
      p.id === proposalId ? { ...p, status: 'Approved' } : p
    );

    setData((prev) => ({
      ...prev,
      proposals: updatedProposals,
      grants: [newGrant, ...prev.grants]
    }));

    showToast(`Proposal approved & converted to Active Grant ${newGrantId}!`, 'success');
    setSelectedGrantId(newGrantId);
    setActiveTab('grants');
  };

  // Sub-Granting Operations (Strictly Non-FCRA)
  const addSubGrant = (subGrantInput) => {
    const parent = data.grants.find((g) => g.id === subGrantInput.parentGrantId);
    if (!parent) {
      showToast('Parent grant not found.', 'error');
      return;
    }

    if (parent.fundingType === 'FCRA Foreign') {
      showToast('FCRA VIOLATION BAN: Sub-granting is strictly prohibited for Foreign FCRA grants under FCRA Section 7.', 'error');
      return;
    }

    const id = `SUBGRANT-${new Date().getFullYear()}-${Math.floor(10 + Math.random() * 90)}`;
    const newSubGrant = {
      id,
      ...subGrantInput,
      disbursedAmount: Number(subGrantInput.firstTranche || subGrantInput.sanctionedAmount * 0.5),
      status: 'Active',
      tranches: [
        {
          id: 'ST1',
          trancheNo: 1,
          amount: Number(subGrantInput.firstTranche || subGrantInput.sanctionedAmount * 0.5),
          date: new Date().toISOString().slice(0, 10),
          status: 'Disbursed',
          ucSubmitted: false
        }
      ],
      documents: subGrantInput.documents || []
    };

    setData((prev) => ({
      ...prev,
      subGrants: [newSubGrant, ...prev.subGrants]
    }));

    showToast(`Non-FCRA Sub-Grant ${id} awarded to partner ${subGrantInput.subGranteeName}!`);
  };

  const updateSubGrant = (updatedSubGrant) => {
    setData((prev) => ({
      ...prev,
      subGrants: prev.subGrants.map((sg) => (sg.id === updatedSubGrant.id ? updatedSubGrant : sg))
    }));
    showToast(`Sub-Grant ${updatedSubGrant.id} details updated.`);
  };

  // Expense logging
  const addExpense = (expenseInput) => {
    const id = `VOUCH-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
    const newExpense = {
      id,
      ...expenseInput,
      amount: Number(expenseInput.amount),
      documents: expenseInput.documents || []
    };

    const grant = data.grants.find((g) => g.id === expenseInput.grantId);
    let updatedGrants = data.grants;

    if (grant) {
      const newSpentAmount = (grant.spentAmount || 0) + Number(expenseInput.amount);
      const updatedBreakdown = (grant.budgetBreakdown || []).map((head) => {
        if (head.category === expenseInput.category) {
          return { ...head, spent: (head.spent || 0) + Number(expenseInput.amount) };
        }
        return head;
      });

      updatedGrants = data.grants.map((g) =>
        g.id === grant.id
          ? {
              ...g,
              spentAmount: newSpentAmount,
              budgetBreakdown: updatedBreakdown
            }
          : g
      );
    }

    setData((prev) => ({
      ...prev,
      expenses: [newExpense, ...prev.expenses],
      grants: updatedGrants
    }));

    showToast(`Expense Voucher ${id} logged with ${newExpense.documents.length} attachment(s)!`);
  };

  const deleteExpense = (expenseId) => {
    const exp = data.expenses.find((e) => e.id === expenseId);
    if (!exp) return;

    const grant = data.grants.find((g) => g.id === exp.grantId);
    let updatedGrants = data.grants;

    if (grant) {
      const newSpentAmount = Math.max(0, (grant.spentAmount || 0) - Number(exp.amount));
      const updatedBreakdown = (grant.budgetBreakdown || []).map((head) => {
        if (head.category === exp.category) {
          return { ...head, spent: Math.max(0, (head.spent || 0) - Number(exp.amount)) };
        }
        return head;
      });

      updatedGrants = data.grants.map((g) =>
        g.id === grant.id
          ? {
              ...g,
              spentAmount: newSpentAmount,
              budgetBreakdown: updatedBreakdown
            }
          : g
      );
    }

    setData((prev) => ({
      ...prev,
      expenses: prev.expenses.filter((e) => e.id !== expenseId),
      grants: updatedGrants
    }));

    showToast(`Voucher ${expenseId} deleted.`, 'info');
  };

  // Close Grant
  const closeGrant = (grantId, closureData) => {
    const grant = data.grants.find((g) => g.id === grantId);
    if (!grant) return;

    const newClosure = {
      grantId,
      grantTitle: grant.title,
      closureDate: new Date().toISOString().slice(0, 10),
      status: 'Formally Closed',
      ...closureData
    };

    const updatedGrants = data.grants.map((g) =>
      g.id === grantId ? { ...g, status: 'Closed' } : g
    );

    setData((prev) => ({
      ...prev,
      grants: updatedGrants,
      closures: [newClosure, ...prev.closures.filter((c) => c.grantId !== grantId)]
    }));

    showToast(`Grant "${grant.title}" formally closed & archived!`, 'success');
  };

  // Demo data reset
  const handleResetDemoData = () => {
    const fresh = resetToDemoData();
    if (fresh) {
      setData({
        ...fresh,
        subGrants: initialSubGrants
      });
      showToast('Sample Indian NGO data & sub-grants loaded!');
    }
  };

  // Export full JSON backup
  const handleExportBackup = () => {
    exportFullBackup(data);
    showToast('NGO Grant Database exported as JSON backup.');
  };

  // Import JSON backup
  const handleImportBackup = (importedData) => {
    try {
      if (importedData && importedData.data) {
        setData(importedData.data);
        showToast('NGO Database successfully imported!');
      } else {
        showToast('Invalid backup file structure.', 'error');
      }
    } catch (e) {
      showToast('Failed to parse backup JSON file.', 'error');
    }
  };

  return (
    <GrantContext.Provider
      value={{
        ngoProfile: data.profile,
        grants: data.grants,
        proposals: data.proposals,
        expenses: data.expenses,
        closures: data.closures,
        subGrants: data.subGrants || initialSubGrants,
        activeTab,
        setActiveTab,
        selectedGrantId,
        setSelectedGrantId,
        selectedProposalId,
        setSelectedProposalId,
        notification,
        showToast,
        updateProfile,
        addProposal,
        updateProposal,
        sanctionProposalToGrant,
        addSubGrant,
        updateSubGrant,
        addExpense,
        deleteExpense,
        closeGrant,
        handleResetDemoData,
        handleExportBackup,
        handleImportBackup
      }}
    >
      {children}
    </GrantContext.Provider>
  );
};

export const useGrant = () => {
  const context = useContext(GrantContext);
  if (!context) {
    throw new Error('useGrant must be used within a GrantProvider');
  }
  return context;
};
