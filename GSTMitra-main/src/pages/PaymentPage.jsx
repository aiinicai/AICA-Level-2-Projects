import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';
import { submitPaymentDetails } from '../firebase/auth';
// Using online QR code generator instead of problematic qrcode.react library
import { CheckCircle, AlertCircle, Send, Upload, X, ArrowRight } from 'lucide-react';

const PaymentPage = () => {
  const { currentUser } = useAuth();
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [gstNumber, setGstNumber] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [upiTxnId, setUpiTxnId] = useState('');
  const [gmailId, setGmailId] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [error, setError] = useState('');

  // UPI payment link for QR code
  const upiLink = `upi://pay?pa=het7660@okicici&pn=Het%20Patel&am=589.00&cu=INR`;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentUser) {
      setError('You must be logged in to submit payment details.');
      return;
    }
    if (!name || !upiTxnId || !companyName || !phoneNumber || !gmailId) {
      setError('Please fill all required fields.');
      return;
    }
    if (!gmailId.includes('@')) {
      setError('Please enter a valid email address (must contain @).');
      return;
    }
    setStatus('loading');
    setError('');
    const result = await submitPaymentDetails({
      uid: currentUser.uid,
      name,
      companyName,
      gstNumber,
      phoneNumber,
      upiTxnId,
      gmailId,
    });
    if (result.success) {
      // Mark payment_pending in user doc for admin review
      try {
        const { doc, updateDoc } = await import('firebase/firestore');
        const { db } = await import('../firebase/config');
        await updateDoc(doc(db, 'users', currentUser.uid), { payment_pending: true });
      } catch (e) { /* ignore error */ }
      setStatus('success');
    } else {
      setStatus('error');
      setError(result.error || 'An unknown error occurred.');
    }
  };

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md bg-dark-card p-8 rounded-2xl shadow-lg text-center"
        >
          <CheckCircle className="mx-auto text-accent-green mb-4" size={60} />
          <h1 className="text-2xl font-bold mb-2">Submission Successful!</h1>
          <p className="text-text-secondary">
            Your payment is being verified. Access will be granted within 24 hours once confirmed. Thank you for your patience.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-dark-bg text-text-primary p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-4xl bg-dark-card p-8 rounded-2xl shadow-lg border border-dark-border"
      >
        {step === 1 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold">Unlock 1-Year Access</h1>
              <p className="text-text-secondary mt-2">Step 1: Complete the payment.</p>
            </div>
            
            <div className="flex flex-col md:flex-row gap-8 md:gap-12 items-stretch">
              {/* Left Side: Price Breakdown */}
              <div className="w-full md:w-1/2">
                <div className="bg-dark-bg rounded-lg p-6 border border-dark-border">
                  <div className="flex justify-between items-center text-text-secondary text-base mb-3">
                    <span>Base Amount</span>
                    <span>₹499.00</span>
                  </div>
                  <div className="flex justify-between items-center text-text-secondary text-base mb-3">
                    <span>CGST (9%)</span>
                    <span>₹44.91</span>
                  </div>
                  <div className="flex justify-between items-center text-text-secondary text-base mb-5">
                    <span>SGST (9%)</span>
                    <span>₹44.91</span>
                  </div>
                  <div className="border-t border-dark-border my-4"></div>
                  <div className="flex justify-between items-center text-text-primary font-bold text-xl">
                    <span>Total Payable</span>
                    <span>₹589.00</span>
                  </div>
                </div>
                
                {/* Payment Instructions */}
                <div className="mt-6 p-6 bg-gray-900 border border-gray-700 rounded-lg">
                  <p className="text-lg font-medium text-gray-200 mb-3">📝 Payment Instructions:</p>
                  <p className="text-base text-gray-400 mb-4">
                    In the transaction description, please add:
                  </p>
                  <div className="font-mono bg-gray-800 border border-gray-600 px-4 py-3 rounded text-base text-gray-100">
                    {currentUser?.email ? `${currentUser.email} - GSTMitra` : 'your@email.com - GSTMitra'}
                  </div>
                </div>
              </div>

              {/* Right Side: QR Code */}
              <div className="w-full md:w-1/2 flex flex-col items-center justify-center bg-white p-6 rounded-2xl shadow-lg text-center">


                <div className="bg-white p-2 rounded-lg">
                  <img 
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(upiLink)}`}
                    alt="UPI QR Code"
                    className="w-64 h-64 rounded-lg"
                  />
                </div>

                <div className="mt-4 text-gray-700">
                  <p className="font-medium">UPI ID: het7660@okicici</p>
                  <p className="text-sm text-gray-500 mt-1">Scan with any UPI app</p>
                </div>
                

              </div>
            </div>

            <div className="mt-8 text-center">
              <button
                onClick={() => setStep(2)}
                className="w-full md:w-auto bg-gradient-to-r from-accent-blue to-accent-green text-white font-bold py-3 px-10 rounded-lg text-lg shadow-lg flex items-center justify-center gap-2 mx-auto"
              >
                I have paid, Proceed <ArrowRight size={20} />
              </button>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="text-center mb-6">
              <h1 className="text-3xl font-bold">Submit Details</h1>
              <p className="text-text-secondary">Step 2: Fill in your details for verification.</p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary mb-2">Invoice Details</h2>
              <div>
                <label htmlFor="gmailId" className="block text-sm font-medium text-text-secondary mb-1">Gmail ID*</label>
                <input
                  type="email"
                  id="gmailId"
                  value={gmailId}
                  onChange={(e) => setGmailId(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 focus:ring-accent-blue focus:border-accent-blue"
                  required
                  placeholder="yourname@gmail.com"
                />
              </div>
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-text-secondary mb-1">Full Name*</label>
                <input
                  type="text"
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 focus:ring-accent-blue focus:border-accent-blue"
                  required
                />
              </div>
              <div>
                <label htmlFor="companyName" className="block text-sm font-medium text-text-secondary mb-1">Company Name*</label>
                <input
                  type="text"
                  id="companyName"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 focus:ring-accent-blue focus:border-accent-blue"
                  required
                />
              </div>
              <div>
                <label htmlFor="phoneNumber" className="block text-sm font-medium text-text-secondary mb-1">Phone Number*</label>
                <input
                  type="tel"
                  id="phoneNumber"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 focus:ring-accent-blue focus:border-accent-blue"
                  required
                />
              </div>
              <div>
                <label htmlFor="gstNumber" className="block text-sm font-medium text-text-secondary mb-1">GST Number (Optional)</label>
                <input
                  type="text"
                  id="gstNumber"
                  value={gstNumber}
                  onChange={(e) => setGstNumber(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 focus:ring-accent-blue focus:border-accent-blue"
                />
              </div>
              <div>
                <label htmlFor="upiTxnId" className="block text-sm font-medium text-text-secondary mb-1">UPI Transaction ID*</label>
                <input
                  type="text"
                  id="upiTxnId"
                  value={upiTxnId}
                  onChange={(e) => setUpiTxnId(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 focus:ring-accent-blue focus:border-accent-blue"
                  required
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 text-red-400 text-sm">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
              <button
                type="submit"
                disabled={status === 'loading'}
                className="w-full bg-gradient-to-r from-accent-green to-accent-blue text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {status === 'loading' ? 'Submitting...' : 'Submit for Verification'}
                {status !== 'loading' && <Send size={20} />}
              </button>
            </form>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default PaymentPage;
