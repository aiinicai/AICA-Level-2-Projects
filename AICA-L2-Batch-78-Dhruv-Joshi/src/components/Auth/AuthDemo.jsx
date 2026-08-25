import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { User, Database, Shield } from 'lucide-react';

const AuthDemo = () => {
  const { currentUser, userData, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
        <div className="text-center">
          <Shield className="w-12 h-12 text-blue-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Authentication Required
          </h3>
          <p className="text-gray-600">
            Please sign in to see your user information and access protected features.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
      <div className="flex items-center space-x-3 mb-4">
        <User className="w-8 h-8 text-green-600" />
        <h3 className="text-lg font-semibold text-gray-900">
          Authentication Success!
        </h3>
      </div>
      
      <div className="space-y-3">
        <div className="bg-white rounded p-3">
          <p className="text-sm font-medium text-gray-700">User ID (UID):</p>
          <p className="text-sm text-gray-600 font-mono break-all">
            {currentUser.uid}
          </p>
        </div>
        
        <div className="bg-white rounded p-3">
          <p className="text-sm font-medium text-gray-700">Email:</p>
          <p className="text-sm text-gray-600">{currentUser.email}</p>
        </div>
        
        <div className="bg-white rounded p-3">
          <p className="text-sm font-medium text-gray-700">Display Name:</p>
          <p className="text-sm text-gray-600">
            {userData?.displayName || currentUser.displayName || 'Not set'}
          </p>
        </div>
        
        <div className="bg-white rounded p-3">
          <p className="text-sm font-medium text-gray-700">Provider:</p>
          <p className="text-sm text-gray-600 capitalize">
            {userData?.provider || 'Unknown'}
          </p>
        </div>
        
        {userData?.createdAt && (
          <div className="bg-white rounded p-3">
            <p className="text-sm font-medium text-gray-700">Account Created:</p>
            <p className="text-sm text-gray-600">
              {new Date(userData.createdAt).toLocaleDateString()}
            </p>
          </div>
        )}
      </div>
      
      <div className="mt-4 p-3 bg-blue-50 rounded">
        <div className="flex items-center space-x-2">
          <Database className="w-4 h-4 text-blue-600" />
          <p className="text-sm text-blue-800">
            User data is stored in Firestore for database tracking
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthDemo;
