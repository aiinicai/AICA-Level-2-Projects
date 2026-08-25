import React from 'react';
import { motion } from 'framer-motion';
import { FileText, ArrowRight, CheckCircle } from 'lucide-react';

const ProcessingScreen = () => {
  const steps = [
    { text: 'Reading Your GSTR-2B file...', delay: 0 },
    { text: 'Reading Government Provided GSTR-2A file...', delay: 0.5 },
    { text: 'Matching invoices...', delay: 1 },
    { text: 'Identifying discrepancies...', delay: 1.5 },
    { text: 'Finalizing your private report...', delay: 2 }
  ];

  const particleVariants = {
    animate: {
      x: [0, 100, 200],
      opacity: [0, 1, 0],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut"
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-16"
      >
        <h1 className="text-3xl md:text-4xl font-bold mb-4 text-text-primary">
          Processing Your Files
        </h1>
        <p className="text-text-secondary text-lg">
          Analyzing invoices securely on your device...
        </p>
      </motion.div>

      {/* Animation Section */}
      <div className="relative mb-16">
        <div className="flex items-center justify-center space-x-16">
          {/* GSTR-1 File Icon */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="flex flex-col items-center"
          >
            <div className="neumorphic-card p-6 mb-4">
              <FileText className="w-12 h-12 text-accent-green" />
            </div>
            <span className="text-sm text-text-secondary">Your GSTR-2B</span>
          </motion.div>

          {/* Flowing Particles */}
          <div className="relative w-32 h-16 overflow-hidden">
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute top-1/2 left-0 w-2 h-2 bg-accent-green rounded-full"
                variants={particleVariants}
                animate="animate"
                style={{ animationDelay: `${i * 0.3}s` }}
              />
            ))}
            <ArrowRight className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-text-secondary w-6 h-6" />
          </div>

          {/* Processing Center */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex flex-col items-center"
          >
            <div className="neumorphic-card p-8 mb-4 relative">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-16 h-16 border-4 border-accent-blue border-t-transparent rounded-full"
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-accent-blue" />
              </div>
            </div>
            <span className="text-sm text-text-secondary">Reconciling</span>
          </motion.div>

          {/* Flowing Particles */}
          <div className="relative w-32 h-16 overflow-hidden">
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute top-1/2 left-0 w-2 h-2 bg-accent-blue rounded-full"
                variants={particleVariants}
                animate="animate"
                style={{ animationDelay: `${i * 0.3 + 1}s` }}
              />
            ))}
            <ArrowRight className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-text-secondary w-6 h-6" />
          </div>

          {/* GSTR-2A File Icon */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex flex-col items-center"
          >
            <div className="neumorphic-card p-6 mb-4">
              <FileText className="w-12 h-12 text-accent-blue" />
            </div>
            <span className="text-sm text-text-secondary">Government Provided GSTR-2A</span>
          </motion.div>
        </div>
      </div>

      {/* Progress Steps */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6 }}
        className="space-y-4 max-w-md w-full"
      >
        {steps.map((step, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: step.delay }}
            className="flex items-center space-x-3"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3, delay: step.delay + 0.2 }}
              className="w-2 h-2 bg-accent-green rounded-full"
            />
            <span className="text-text-secondary">{step.text}</span>
          </motion.div>
        ))}
      </motion.div>

      {/* Privacy Reminder */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 2.5 }}
        className="mt-16 text-center"
      >
        <p className="text-text-secondary text-sm">
          🔒 All processing happens locally on your device
        </p>
      </motion.div>
    </div>
  );
};

export default ProcessingScreen;
