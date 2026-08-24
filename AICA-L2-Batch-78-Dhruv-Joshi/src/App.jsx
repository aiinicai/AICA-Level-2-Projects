import { Analytics } from '@vercel/analytics/react';
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from './contexts/AuthContext';
import LandingScreen from '../components/LandingScreen.jsx';
import AuthModal from './components/Auth/AuthModal.jsx';
import ProcessingScreen from '../components/ProcessingScreen.jsx';
import ResultsScreen from '../components/ResultsScreen.jsx';
import ColumnMappingScreen from '../components/ColumnMappingScreen.jsx';
import Profile from '../components/Profile.jsx';
import { reconcileGSTFiles, parseCsvForMapping } from './utils/reconciliation';
import { doc, getDoc } from 'firebase/firestore';
import { db } from './firebase/config';

function App() {
  const [pendingAction, setPendingAction] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [currentScreen, setCurrentScreen] = useState('landing'); // 'landing', 'mapping', 'processing', 'results', 'profile'
  const [gstr1File, setGstr1File] = useState(null);
  const [gstr2File, setGstr2File] = useState(null);
  const [gstr2Type, setGstr2Type] = useState('2A'); // '2A' or '2B'
    const [reconciliationResults, setReconciliationResults] = useState(null);
  const [isProfileComplete, setIsProfileComplete] = useState(false);
  const [isCheckingProfile, setIsCheckingProfile] = useState(true);

  // State for column mapping
  const [gstr1MapData, setGstr1MapData] = useState({});
  const [gstr2MapData, setGstr2MapData] = useState({});
  const [gstr1Mapping, setGstr1Mapping] = useState(null);
  const [gstr2Mapping, setGstr2Mapping] = useState(null);
  const [gstr1StartRow, setGstr1StartRow] = useState(2);
  const [gstr2StartRow, setGstr2StartRow] = useState(2);

  const handleGstr1Uploaded = (file) => {
    setGstr1File(file);
  };

  const handleGstr2Uploaded = (file) => {
    setGstr2File(file);
  };

    const { currentUser } = useAuth();
const handleStartComparison = async () => {
    const isGstr1Csv = gstr1File && gstr1File.name.endsWith('.csv');
    const isGstr2Csv = gstr2File && gstr2File.name.endsWith('.csv');

    // If either file is a CSV and we haven't mapped yet, go to mapping screen
    if ((isGstr1Csv && !gstr1Mapping) || (isGstr2Csv && !gstr2Mapping)) {
      if (isGstr1Csv) {
        const { headers, preview } = await parseCsvForMapping(gstr1File);
        setGstr1MapData({ headers, preview });
      }
      if (isGstr2Csv) {
        const { headers, preview } = await parseCsvForMapping(gstr2File);
        setGstr2MapData({ headers, preview });
      }
      setCurrentScreen('mapping');
      return;
    }

    // Proceed to reconciliation
    setCurrentScreen('processing');
  };

  useEffect(() => {
    // This effect triggers reconciliation after mapping is complete or if no mapping was needed
    if (currentScreen === 'processing') {
      const reconcile = async () => {
        try {
          await new Promise(resolve => setTimeout(resolve, 2000));
          const results = await reconcileGSTFiles(gstr1File, gstr2File, gstr2Type, gstr1Mapping, gstr2Mapping, gstr1StartRow, gstr2StartRow);
          setReconciliationResults(results);
          setCurrentScreen('results');
        } catch (error) {
          console.error('Error during reconciliation:', error);
          alert('Error processing files. Please check your file format and try again.');
          handleStartOver();
        }
      };
      reconcile();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentScreen, gstr1File, gstr2File, gstr2Type, gstr1Mapping, gstr2Mapping, gstr1StartRow, gstr2StartRow]);

  useEffect(() => {
    const checkProfileCompletion = async () => {
      if (!currentUser) {
        setIsProfileComplete(false);
        setIsCheckingProfile(false);
        setCurrentScreen('landing');
        return;
      }

      setIsCheckingProfile(true);
      try {
        const profileRef = doc(db, 'profiles', currentUser.uid);
        const docSnap = await getDoc(profileRef);

        if (docSnap.exists()) {
          const data = docSnap.data();
          if (data.firstName && data.lastName && data.mobile) {
            setIsProfileComplete(true);
            setCurrentScreen('landing');
          } else {
            setIsProfileComplete(false);
            setCurrentScreen('profile');
          }
        } else {
          setIsProfileComplete(false);
          setCurrentScreen('profile');
        }
      } catch (error) {
        console.error("Error checking profile completion:", error);
        setIsProfileComplete(false);
        setCurrentScreen('profile');
      }
      setIsCheckingProfile(false);
    };

    checkProfileCompletion();
  }, [currentUser]);

  const handleMappingComplete = (gstr1Map, gstr2Map, gstr1Row, gstr2Row) => {
    setGstr1Mapping(gstr1Map);
    setGstr2Mapping(gstr2Map);
    setGstr1StartRow(gstr1Row);
    setGstr2StartRow(gstr2Row);
    // Use a timeout to allow state to update before proceeding
    setTimeout(() => setCurrentScreen('processing'), 100);
  };

    const handleProfileComplete = () => {
    setIsProfileComplete(true);
    setCurrentScreen('landing');
  };

  const handleEditProfile = () => {
    setCurrentScreen('profile');
  };

  const handleStartOver = () => {
    setCurrentScreen('landing');
    setGstr1File(null);
    setGstr2File(null);
    setGstr2Type('2A');
    setReconciliationResults(null);
    setGstr1Mapping(null);
    setGstr2Mapping(null);
    setGstr1MapData({});
    setGstr2MapData({});
    setGstr1StartRow(2);
    setGstr2StartRow(2);
  };

  if (isCheckingProfile) {
    return <ProcessingScreen message="Checking your profile..." />;
  }

  const renderScreen = () => {
    if (!currentUser) {
      return <LandingScreen onAuthRequest={() => setAuthModalOpen(true)} />;
    }

    if (!isProfileComplete || currentScreen === 'profile') {
      return <Profile onProfileComplete={handleProfileComplete} onCancel={() => setCurrentScreen('landing')} />;
    }

    switch (currentScreen) {
      case 'landing':
                return <LandingScreen onGstr1Uploaded={handleGstr1Uploaded} onGstr2Uploaded={handleGstr2Uploaded} onStartComparison={handleStartComparison} onEditProfile={handleEditProfile} gstr1File={gstr1File} gstr2File={gstr2File} />;
      case 'mapping':
        return (
          <ColumnMappingScreen
            gstr1={gstr1MapData}
            gstr2={gstr2MapData}
            onMappingComplete={handleMappingComplete}
            onCancel={handleStartOver}
          />
        );
      case 'processing':
        return <ProcessingScreen />;
      case 'results':
        return <ResultsScreen results={reconciliationResults} onStartOver={handleStartOver} />;
      default:
                return <LandingScreen onGstr1Uploaded={handleGstr1Uploaded} onGstr2Uploaded={handleGstr2Uploaded} onStartComparison={handleStartComparison} onEditProfile={handleEditProfile} gstr1File={gstr1File} gstr2File={gstr2File} />;
    }
  };

  return (
    <div className="min-h-screen bg-dark-bg text-text-primary">
      <AnimatePresence mode="wait">
        <motion.div
          key={currentScreen}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
          {renderScreen()}
        </motion.div>
      </AnimatePresence>
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
      <Analytics />
    </div>
  );
}

export default App;
