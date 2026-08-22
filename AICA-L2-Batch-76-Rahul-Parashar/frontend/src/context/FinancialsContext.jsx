import { createContext, useContext, useMemo, useState } from 'react';

const FinancialsContext = createContext(null);

export function FinancialsProvider({ children }) {
  const [financials, setFinancials] = useState(null);
  const [dashboardReady, setDashboardReady] = useState(false);
  const [displayUnit, setDisplayUnit] = useState('L');
  const [peer, setPeer] = useState(null); // { name, financials } | null

  const resetFile = () => {
    setFinancials(null);
    setDashboardReady(false);
    setPeer(null);
  };

  const value = useMemo(
    () => ({
      financials,
      setFinancials,
      dashboardReady,
      setDashboardReady,
      displayUnit,
      setDisplayUnit,
      resetFile,
      peer,
      setPeer,
    }),
    [financials, dashboardReady, displayUnit, peer]
  );

  return <FinancialsContext.Provider value={value}>{children}</FinancialsContext.Provider>;
}

export function useFinancials() {
  const ctx = useContext(FinancialsContext);
  if (!ctx) throw new Error('useFinancials must be used within a FinancialsProvider');
  return ctx;
}
