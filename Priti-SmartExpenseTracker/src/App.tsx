/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { TransactionHistory } from './components/TransactionHistory';
import { TransactionModal } from './components/TransactionModal';
import { ScanInvoiceModal } from './components/ScanInvoiceModal';
import { FAB } from './components/FAB';
import { OfflineIndicator } from './components/OfflineIndicator';
import { Transaction } from './types';
import {
  getStoredTransactions,
  addTransaction,
  updateTransaction,
  deleteTransaction,
  resetToSampleTransactions,
} from './utils/storage';

export default function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'history'>('dashboard');
  const [currentMonth, setCurrentMonth] = useState<string>('2026-09');

  // Modals state
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);

  // Toast / notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Initialize transactions from local storage
  useEffect(() => {
    const stored = getStoredTransactions();
    setTransactions(stored);
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const handleSaveTransaction = (
    txData: Omit<Transaction, 'id' | 'createdAt'>
  ) => {
    if (editingTransaction) {
      const updatedTx: Transaction = {
        ...editingTransaction,
        ...txData,
      };
      updateTransaction(updatedTx);
      setTransactions((prev) =>
        prev.map((t) => (t.id === updatedTx.id ? updatedTx : t))
      );
      setEditingTransaction(null);
      showToast('Transaction updated successfully');
    } else {
      const newTx = addTransaction(txData);
      setTransactions((prev) => [newTx, ...prev]);
      showToast(
        txData.source === 'image'
          ? 'Invoice scanned & saved successfully'
          : 'Transaction added successfully'
      );
    }
  };

  const handleDeleteTransaction = (id: string) => {
    deleteTransaction(id);
    setTransactions((prev) => prev.filter((t) => t.id !== id));
    showToast('Transaction deleted');
  };

  const handleEditTransaction = (tx: Transaction) => {
    setEditingTransaction(tx);
    setIsManualModalOpen(true);
  };

  const handleResetData = () => {
    const sample = resetToSampleTransactions();
    setTransactions(sample);
    showToast('Reset to demo transactions dataset');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        transactions={transactions}
        onResetData={handleResetData}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {activeTab === 'dashboard' ? (
          <Dashboard
            transactions={transactions}
            currentMonth={currentMonth}
            onMonthChange={setCurrentMonth}
            onOpenScanModal={() => setIsScanModalOpen(true)}
            onOpenManualModal={() => {
              setEditingTransaction(null);
              setIsManualModalOpen(true);
            }}
            onNavigateToHistory={() => setActiveTab('history')}
          />
        ) : (
          <TransactionHistory
            transactions={transactions}
            onEdit={handleEditTransaction}
            onDelete={handleDeleteTransaction}
            onOpenScanModal={() => setIsScanModalOpen(true)}
            onOpenManualModal={() => {
              setEditingTransaction(null);
              setIsManualModalOpen(true);
            }}
          />
        )}
      </main>

      {/* Floating Action Button (FAB) */}
      <FAB
        onScanInvoice={() => setIsScanModalOpen(true)}
        onAddManual={() => {
          setEditingTransaction(null);
          setIsManualModalOpen(true);
        }}
      />

      {/* Manual Entry & Edit Modal */}
      <TransactionModal
        isOpen={isManualModalOpen}
        onClose={() => {
          setIsManualModalOpen(false);
          setEditingTransaction(null);
        }}
        onSave={handleSaveTransaction}
        editingTransaction={editingTransaction}
      />

      {/* AI Invoice Scanner Modal */}
      <ScanInvoiceModal
        isOpen={isScanModalOpen}
        onClose={() => setIsScanModalOpen(false)}
        onSave={handleSaveTransaction}
      />

      {/* Offline Status Badge */}
      <OfflineIndicator />

      {/* Subtle Toast Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-xs font-semibold shadow-2xl animate-in fade-in slide-in-from-bottom-2">
          {toastMessage}
        </div>
      )}
    </div>
  );
}
