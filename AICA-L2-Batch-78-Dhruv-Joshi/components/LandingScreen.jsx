import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, Shield, Zap, FileText } from 'lucide-react';
import FileUploadZone from './FileUploadZone';
import AuthHeader from '../src/components/Auth/AuthHeader.jsx';
import SubscriptionTiers from '../src/components/SubscriptionTiers';
import { useAuth } from '../src/contexts/AuthContext';
import { checkAndIncrementUsage } from '../src/firebase/auth';

const LandingScreen = ({ 
  onGstr1Uploaded,
  onGstr2Uploaded,
  onStartComparison, 
  onEditProfile, 
  gstr1File, 
  gstr2File
}) => {
  const { currentUser, currentPlan } = useAuth();
  const navigate = useNavigate();

  const isReadyToCompare = gstr1File && gstr2File;

  return (
    <div className="min-h-screen flex flex-col bg-dark-bg px-4 py-6 sm:px-6 lg:px-8">
      {/* Auth Header */}
      <div className="w-full flex justify-end p-2 sm:p-4">
        <div className="flex items-center space-x-4">
          <button onClick={onEditProfile} className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors">
            Edit Profile
          </button>
          <AuthHeader />
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="w-full flex flex-col items-center justify-center max-w-5xl lg:max-w-6xl xl:max-w-7xl mx-auto space-y-8 sm:space-y-12">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-center"
      >
        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-3 sm:mb-4 bg-gradient-to-r from-accent-green to-accent-blue bg-clip-text text-transparent">
          GSTMitra
        </h1>
        <h2 className="text-lg sm:text-xl md:text-2xl lg:text-3xl font-semibold mb-3 sm:mb-4 text-text-primary">
          Reconcile GSTR Files. Instantly & Privately.
        </h2>
        <p className="text-text-secondary max-w-md sm:max-w-2xl lg:max-w-3xl mx-auto text-base sm:text-lg lg:text-xl">
          Your data is never uploaded or stored. All processing happens securely on your device.
        </p>
      </motion.div>

      {/* Privacy Features */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="flex flex-wrap justify-center gap-4 sm:gap-6"
      >
        <div className="flex items-center gap-2 text-accent-green">
          <Shield size={20} />
          <span className="text-sm font-medium">100% Private</span>
        </div>
        <div className="flex items-center gap-2 text-accent-blue">
          <Zap size={20} />
          <span className="text-sm font-medium">Instant Results</span>
        </div>
        <div className="flex items-center gap-2 text-accent-purple">
          <FileText size={20} />
          <span className="text-sm font-medium">No Registration</span>
        </div>
      </motion.div>

      

      {/* File Upload Section */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.4 }}
        className="w-full max-w-3xl lg:max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 lg:gap-12 mx-auto"
      >
        {/* GSTR-1 Upload */}
        <div className="w-full">
          <FileUploadZone
            title="Upload Your GSTR-2B File"
            subtitle="Your GSTR-2B data (from your records)"
            acceptedFormats=".json,.csv"
            file={gstr1File}
            onFileUpload={onGstr1Uploaded}
            accentColor="accent-green"
          />
        </div>

        {/* GSTR-2A/2B Upload */}
        <div className="w-full">
          <FileUploadZone
            title={`Upload Government Provided GSTR-2B File`}
            subtitle={`Government Provided GSTR-2B (downloaded from GST portal)`}
            acceptedFormats=".json,.csv"
            file={gstr2File}
            onFileUpload={onGstr2Uploaded}
            accentColor="accent-blue"
          />
        </div>
      </motion.div>

      {/* Compare Button */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, delay: 0.6 }}
        className="flex justify-center w-full"
      >
        <button
          onClick={async () => {
            if (!isReadyToCompare) return;
            if (!currentUser) {
              console.log('DEBUG: No current user, cannot proceed');
              return;
            }

            console.log('DEBUG: Checking usage for user:', currentUser.uid);
            console.log('DEBUG: Calling checkAndIncrementUsage with uid:', currentUser?.uid);
            const result = await checkAndIncrementUsage(currentUser.uid);
            console.log('DEBUG: Frontend received usage check result:', result);
            console.log('DEBUG: Usage check result:', result);
            console.log('DEBUG: Result.canAccess is:', result.canAccess);
            
            if (result.canAccess) {
              console.log('DEBUG: Access granted, starting comparison');
              onStartComparison();
            } else {
              console.log('DEBUG: Access denied. Reason:', result.reason, 'Message:', result.message);
              // If access is denied due to an ad blocker or network issue, show a specific alert.
              if (result.reason === 'ad_blocker_or_network') {
                alert(result.message); // Show the specific error message to the user
              } else {
                // For all other reasons (e.g., usage limit reached), redirect to payment.
                navigate('/payment');
              }
            }
          }}
          disabled={!isReadyToCompare}
          className={`bg-white text-black font-bold text-base sm:text-lg px-6 sm:px-12 py-3 sm:py-4 rounded-xl shadow-md transition-colors duration-300 w-full sm:w-auto ${
            isReadyToCompare
              ? 'hover:bg-gray-200'
              : 'opacity-50 cursor-not-allowed'
          }`}
        >
          {isReadyToCompare ? 'Compare Now' : 'Upload Both Files to Continue'}
        </button>

      </motion.div>

      {/* Subscription Tiers */}
      <div className="w-full max-w-7xl mx-auto px-1 sm:px-0">
        <SubscriptionTiers currentPlan={currentPlan} />
      </div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1 }}
        className="text-center text-text-secondary text-xs sm:text-sm pt-6 sm:pt-10 px-2"
      >
        <p>Supports JSON and CSV formats • No data leaves your device</p>
      </motion.div>
        </div>
      </div>
    </div>
  );
};

export default LandingScreen;
