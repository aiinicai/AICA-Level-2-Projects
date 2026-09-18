import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';
import { Company } from '../types';

interface CompanyContextType {
  companies: Company[];
  selectedCompany: Company | null;
  setSelectedCompany: (c: Company | null) => void;
  refreshCompanies: () => Promise<void>;
  loading: boolean;
}

const CompanyContext = createContext<CompanyContextType | undefined>(undefined);

export const CompanyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshCompanies = async () => {
    try {
      const res = await api.get<Company[]>('/companies');
      setCompanies(res.data);
      if (res.data.length > 0) {
        if (!selectedCompany || !res.data.some((c) => c.id === selectedCompany.id)) {
          setSelectedCompany(res.data[0]);
        }
      }
    } catch (e) {
      console.error('Failed to load companies:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('asset_tagging_token');
    if (token) {
      refreshCompanies();
    } else {
      setLoading(false);
    }
  }, []);

  return (
    <CompanyContext.Provider
      value={{
        companies,
        selectedCompany,
        setSelectedCompany,
        refreshCompanies,
        loading,
      }}
    >
      {children}
    </CompanyContext.Provider>
  );
};

export const useCompany = () => {
  const context = useContext(CompanyContext);
  if (!context) {
    throw new Error('useCompany must be used within a CompanyProvider');
  }
  return context;
};
