import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { signOutUser } from '../../firebase/auth';
import { User, LogOut, Mail, Calendar, Shield } from 'lucide-react';

const UserProfile = ({ onClose, onProfile }) => {
  const { currentUser, userData } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleSignOut = async () => {
    setLoading(true);
    await signOutUser();
    setLoading(false);
    onClose && onClose();
  };

  if (!currentUser) return null;

  return (
    <div className="bg-dark-card rounded-lg shadow-lg p-6 w-80 border border-dark-border">
      <div className="flex items-center space-x-4 mb-6">
        {currentUser.photoURL ? (
          <img
            src={currentUser.photoURL}
            alt="Profile"
            className="w-16 h-16 rounded-full"
          />
        ) : (
          <div className="w-16 h-16 bg-gradient-to-br from-accent-blue to-accent-green rounded-full flex items-center justify-center">
            <User className="w-8 h-8 text-white" />
          </div>
        )}
        <div>
          <h3 className="text-lg font-semibold text-text-primary">
            {userData?.displayName || currentUser.displayName || 'User'}
          </h3>
          <p className="text-sm text-text-secondary">
            {userData?.provider === 'google' ? 'Google Account' : 'Email Account'}
          </p>
        </div>
      </div>

      <div className="space-y-4 mb-6">
      
        <div className="flex items-center space-x-3 text-sm">
          <Mail className="w-4 h-4 text-text-secondary" />
          <span className="text-text-primary">{currentUser.email}</span>
        </div>
        
        <div className="flex items-center space-x-3 text-sm">
          <Shield className="w-4 h-4 text-text-secondary" />
          <span className="text-text-primary">UID: {currentUser.uid.substring(0, 8)}...</span>
        </div>

        {userData?.createdAt && (
          <div className="flex items-center space-x-3 text-sm">
            <Calendar className="w-4 h-4 text-text-secondary" />
            <span className="text-text-primary">
              Joined {new Date(userData.createdAt).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>

      <button
        onClick={handleSignOut}
        disabled={loading}
        className="w-full bg-dark-bg text-text-primary py-2 px-4 rounded-lg hover:bg-red-800 hover:text-white focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors duration-200"
      >
        {loading ? (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
        ) : (
          <>
            <LogOut className="w-4 h-4" />
            Sign Out
          </>
        )}
      </button>
    </div>
  );
};

export default UserProfile;
