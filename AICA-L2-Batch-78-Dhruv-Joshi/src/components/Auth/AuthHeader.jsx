import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { User, LogIn } from 'lucide-react';
import AuthModal from './AuthModal';
import UserProfile from './UserProfile';

const AuthHeader = ({ onProfile }) => {
  const { isAuthenticated, currentUser } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUserProfile, setShowUserProfile] = useState(false);

  const handleAuthSuccess = (user) => {
    console.log('User authenticated:', user.uid);
    setShowAuthModal(false);
  };

  return (
    <>
      <div className="flex items-center space-x-4">
        {isAuthenticated ? (
          <div className="relative">
            <button
              onClick={() => setShowUserProfile(!showUserProfile)}
              className="flex items-center space-x-2 bg-blue-50 hover:bg-blue-100 px-3 py-2 rounded-lg transition-colors"
            >

              <span className="text-sm font-medium text-gray-700">
                {currentUser?.displayName?.split(' ')[0] || 'User'}
              </span>
            </button>
            
            {showUserProfile && (
              <div className="absolute right-0 top-full mt-2 z-50">
                <UserProfile onClose={() => setShowUserProfile(false)} onProfile={onProfile} />
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setShowAuthModal(true)}
            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <LogIn className="w-4 h-4" />
            <span>Sign In</span>
          </button>
        )}
      </div>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />
    </>
  );
};

export default AuthHeader;
