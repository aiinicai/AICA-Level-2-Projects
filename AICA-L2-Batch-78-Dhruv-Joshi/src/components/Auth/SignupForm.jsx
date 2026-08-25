import React, { useState } from 'react';
import { signUpWithEmail, signInWithGoogle, getUserData } from '../../firebase/auth';
import { doc, updateDoc } from 'firebase/firestore';
import { db } from '../../firebase/config';
import ProfileInfoModal from './ProfileInfoModal';
import { Mail, Lock, User, Eye, EyeOff, UserPlus } from 'lucide-react';

const SignupForm = ({ onToggleForm, onSuccess }) => {
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileModalData, setProfileModalData] = useState({ displayName: '', phoneNumber: '' });
  const [pendingGoogleUser, setPendingGoogleUser] = useState(null);
  const [isNewGoogleUser, setIsNewGoogleUser] = useState(false);
  const [formData, setFormData] = useState({
    displayName: '',
    email: '',
    phoneNumber: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const validateForm = () => {
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return false;
    }
    if (!formData.displayName.trim()) {
      setError('Name is required');
      return false;
    }
    if (!formData.phoneNumber.trim() || !/^\d{10}$/.test(formData.phoneNumber.trim())) {
      setError('Valid 10-digit phone number is required');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    setError('');

    const { user, error } = await signUpWithEmail(
      formData.email, 
      formData.password, 
      formData.displayName,
      formData.phoneNumber
    );
    
    if (error) {
      setError(error);
    } else {
      // Facebook Pixel: Lead only on successful new email registration
      if (typeof window !== 'undefined' && window.fbq) {
        window.fbq('track', 'Lead');
      }
      onSuccess && onSuccess(user);
    }
    
    setLoading(false);
  };

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError('');

    const { user, isNewUser, error } = await signInWithGoogle();
    if (error) {
      setError(error);
      setLoading(false);
      return;
    }
    // Check Firestore for missing info
    const { data: userData } = await getUserData(user.uid);
    if (!userData || !userData.displayName || !userData.phoneNumber) {
      setPendingGoogleUser(user);
      setIsNewGoogleUser(!!isNewUser);
      setProfileModalData({
        displayName: userData?.displayName || user.displayName || '',
        phoneNumber: userData?.phoneNumber || ''
      });
      setProfileModalOpen(true);
      setLoading(false);
      return;
    }
    // If user is new and has all info, fire Lead now
    if (isNewUser && typeof window !== 'undefined' && window.fbq) {
      window.fbq('track', 'Lead');
    }
    onSuccess && onSuccess(user);
    setLoading(false);
  };

  // Handle saving missing profile info after Google sign-in
  const handleProfileModalSave = async ({ displayName, phoneNumber }) => {
    if (!pendingGoogleUser) return;
    try {
      await updateDoc(doc(db, 'users', pendingGoogleUser.uid), {
        displayName,
        phoneNumber
      });
      setProfileModalOpen(false);
      // Fire Lead if this was a new Google user and prevent duplicate fires
      if (isNewGoogleUser && typeof window !== 'undefined' && window.fbq) {
        window.fbq('track', 'Lead');
      }
      setIsNewGoogleUser(false);
      const u = pendingGoogleUser;
      setPendingGoogleUser(null);
      onSuccess && onSuccess(u);
    } catch (err) {
      setError('Failed to save profile info. Please try again.');
    }
  };

  return (
    <div className="bg-gray-800 text-gray-100 rounded-2xl shadow-lg p-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="text-center text-3xl font-extrabold text-white">
          Create your account
        </h2>
      </div>
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          {error && (
            <div className="bg-red-900 border border-red-700 text-red-300 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Display Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  name="displayName"
                  value={formData.displayName}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent placeholder-gray-400"
                  placeholder="Enter your name"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent placeholder-gray-400"
                  placeholder="Enter your email"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Phone Number
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="tel"
                  name="phoneNumber"
                  value={formData.phoneNumber}
                  onChange={handleChange}
                  className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent placeholder-gray-400"
                  placeholder="10-digit Phone Number"
                  required
                  maxLength={10}
                  pattern="\d{10}"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full pl-10 pr-12 py-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent placeholder-gray-400"
                  placeholder="Create a password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-200"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="w-full pl-10 pr-12 py-3 bg-gray-700 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent placeholder-gray-400"
                  placeholder="Confirm your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-200"
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  Create Account
                </>
              )}
            </button>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-600" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-gray-800 text-gray-400">Or continue with</span>
              </div>
            </div>

            <button
              onClick={handleGoogleSignIn}
              disabled={loading}
              className="mt-4 w-full bg-gray-700 border border-gray-600 text-white py-3 px-4 rounded-lg hover:bg-gray-600 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>
          </div>

          <p className="mt-8 text-center text-sm text-gray-400">
            Already have an account?{' '}
            <button
              onClick={onToggleForm}
              className="font-medium text-green-400 hover:text-green-300"
            >
              Sign in
            </button>
          </p>
      </div>
    </div>
  );
};

export default SignupForm;
