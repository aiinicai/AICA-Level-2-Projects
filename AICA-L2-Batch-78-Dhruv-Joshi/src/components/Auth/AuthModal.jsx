import React, { useState } from 'react';
import { X } from 'lucide-react';
import LoginForm from './LoginForm';
import SignupForm from './SignupForm';

const AuthModal = ({ isOpen, onClose, onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);

  if (!isOpen) return null;

  const handleSuccess = (user) => {
    onSuccess && onSuccess(user);
    onClose();
  };

  const toggleForm = () => {
    setIsLogin(!isLogin);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="relative max-w-md w-full">
        <button
          onClick={onClose}
          className="absolute -top-4 -right-4 bg-white rounded-full p-2 shadow-lg hover:bg-gray-100 z-10"
        >
          <X className="w-5 h-5 text-gray-600" />
        </button>
        
        {isLogin ? (
          <LoginForm 
            onToggleForm={toggleForm} 
            onSuccess={handleSuccess}
          />
        ) : (
          <SignupForm 
            onToggleForm={toggleForm} 
            onSuccess={handleSuccess}
          />
        )}
      </div>
    </div>
  );
};

export default AuthModal;
