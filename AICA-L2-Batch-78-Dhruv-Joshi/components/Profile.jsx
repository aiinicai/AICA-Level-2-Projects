import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../src/contexts/AuthContext';
import { getAuth } from 'firebase/auth';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import { db } from '../src/firebase/config';
import { uploadProfileImage } from '../src/firebase/storage';
import { User, Camera, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import './Profile.css';

const Profile = ({ onProfileComplete, onCancel }) => {
  const { currentUser } = useAuth();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [mobile, setMobile] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [gstin, setGstin] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!currentUser) return;
      setIsLoading(true);
      try {
        const docRef = doc(db, 'profiles', currentUser.uid);
        const docSnap = await getDoc(docRef);
        if (docSnap.exists()) {
          const data = docSnap.data();
          setFirstName(data.firstName || '');
          setLastName(data.lastName || '');
          setMobile(data.mobile || '');
          setCompanyName(data.companyName || '');
          setGstin(data.gstin || '');
          setImagePreview(data.photoURL || '');
        }
      } catch (e) {
        console.error("Error fetching profile: ", e);
      }
      setIsLoading(false);
    };
    fetchProfile();
  }, [currentUser]);

  const handleImageChange = (e) => {
    if (e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!firstName || !lastName || !mobile) {
      alert('Please fill out all required fields: First Name, Last Name, and Mobile.');
      return;
    }
    setIsSaving(true);
    try {
      let photoURL = imagePreview;
      if (imageFile) {
        photoURL = await uploadProfileImage(imageFile, currentUser.uid);
      }

      const profileData = {
        firstName,
        lastName,
        mobile,
        companyName,
        gstin,
        photoURL,
        updatedAt: new Date().toISOString(),
      };

      await setDoc(doc(db, 'profiles', currentUser.uid), profileData, { merge: true });

      setIsSaving(false);
      alert('Profile saved successfully!');
      if (typeof onProfileComplete === 'function') {
        onProfileComplete();
      }
    } catch (e) {
      setIsSaving(false);
      console.error("Error saving profile: ", e);
      alert('Failed to save profile. Please try again.');
    }
  };

  if (isLoading) {
    return <div className="loading-container"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <motion.div 
      className="profile-container-cred"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="profile-header">
        <div className="profile-image-wrapper" onClick={() => fileInputRef.current.click()}>
          {imagePreview ? (
            <img src={imagePreview} alt="Profile" className="profile-image" />
          ) : (
            <div className="profile-image-placeholder"><User size={48} /></div>
          )}
          <div className="profile-image-overlay"><Camera size={24} /></div>
          <input type="file" ref={fileInputRef} onChange={handleImageChange} accept="image/*" hidden />
        </div>
        <h2 className="profile-name">{`${firstName} ${lastName}` || 'Complete Your Profile'}</h2>
        <p className="profile-email">{currentUser.email}</p>
      </div>

      <form className="profile-form" onSubmit={handleSave}>
        <div className="input-group">
          <input type="text" placeholder="First Name *" value={firstName} onChange={(e) => setFirstName(e.target.value)} required className="profile-input" />
          <input type="text" placeholder="Last Name *" value={lastName} onChange={(e) => setLastName(e.target.value)} required className="profile-input" />
        </div>
        <input type="tel" placeholder="Mobile Number *" value={mobile} onChange={(e) => setMobile(e.target.value)} required className="profile-input" />
        <input type="text" placeholder="Company Name" value={companyName} onChange={(e) => setCompanyName(e.target.value)} className="profile-input" />
        <input type="text" placeholder="GSTIN" value={gstin} onChange={(e) => setGstin(e.target.value)} className="profile-input" />
        <div className="profile-actions">
          <button type="button" onClick={onCancel} className="cancel-button">
            Back
          </button>
          <button type="submit" className="save-button" disabled={isSaving}>
            {isSaving ? <Loader2 className="animate-spin" /> : 'Save and Continue'}
          </button>
        </div>
      </form>
    </motion.div>
  );
};

export default Profile;





