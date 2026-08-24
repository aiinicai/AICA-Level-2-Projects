import React, { createContext, useContext, useEffect, useState } from 'react';
import { onAuthStateChange, getCurrentUser, getUserData } from '../firebase/auth';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isProfileComplete, setIsProfileComplete] = useState(false);
  const [currentPlan, setCurrentPlan] = useState('free');

  useEffect(() => {
    const unsubscribe = onAuthStateChange(async (user) => {
      if (user) {
        setCurrentUser(user);
        const { data, error } = await getUserData(user.uid);
        if (!error && data) {
          setUserData(data);
          setCurrentPlan(data.plan || 'free');
          setIsProfileComplete(!!(data.firstName && data.lastName && data.mobile));
        } else {
          setUserData(null);
          setCurrentPlan('free');
          setIsProfileComplete(false);
        }
      } else {
        setCurrentUser(null);
        setUserData(null);
        setIsProfileComplete(false);
        setCurrentPlan('free');
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  // Determine if subscription is active
  let isSubscriptionActive = false;
  if (userData && userData.subscription_expiry) {
    let expiryDate;
    if (typeof userData.subscription_expiry === 'string') {
      expiryDate = new Date(userData.subscription_expiry);
    } else if (userData.subscription_expiry.seconds) {
      expiryDate = new Date(userData.subscription_expiry.seconds * 1000);
    }
    isSubscriptionActive = expiryDate > new Date();
  }

  const value = {
    currentUser,
    userData,
    loading,
    isAuthenticated: !!currentUser,
    isProfileComplete,
    currentPlan,
    isSubscriptionActive
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
