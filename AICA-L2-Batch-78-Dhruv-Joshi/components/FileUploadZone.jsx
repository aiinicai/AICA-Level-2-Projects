import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import { Upload, FileText, Check, X } from 'lucide-react';

const FileUploadZone = ({ title, subtitle, acceptedFormats, file, onFileUpload, accentColor = 'accent-green' }) => {
  const [error, setError] = useState('');

  const onDrop = useCallback((acceptedFiles, fileRejections) => {
    if (fileRejections.length > 0) {
      setError('Invalid file type. Please upload a JSON or CSV file.');
      return;
    }
    if (acceptedFiles.length > 0) {
      setError('');
      onFileUpload(acceptedFiles[0]);
    }
  }, [onFileUpload]);

  // Convert acceptedFormats string to proper object format for react-dropzone
  const acceptObject = {
    'application/json': ['.json'],
    'text/csv': ['.csv']
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptObject,
    multiple: false,
  });

  const clearFile = (e) => {
    e.stopPropagation();
    onFileUpload(null);
    setError('');
  };

  const accent = {
    border: `border-${accentColor}`,
    shadow: `shadow-glow-${accentColor.split('-')[1]}`,
    text: `text-${accentColor}`,
  };

  return (
    <motion.div whileHover={{ scale: 1.02 }} className="w-full">
      <div
        {...getRootProps()}
        className={`neumorphic-inset p-6 text-center cursor-pointer transition-all duration-300 relative ${
          isDragActive ? `${accent.border} ${accent.shadow}` : ''
        } ${file ? `${accent.border} ${accent.shadow}` : ''} ${
          error ? 'border-red-500' : ''
        }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-3"
          >
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full bg-${accentColor} bg-opacity-20`}>
              <Check className={`w-8 h-8 ${accent.text}`} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-text-primary">File Selected</h3>
              <p className="text-text-secondary text-sm truncate">{file.name}</p>
            </div>
            <button
              onClick={clearFile}
              className="absolute top-3 right-3 text-red-400 hover:text-red-300 transition-colors z-10"
            >
              <X size={20} />
            </button>
          </motion.div>
        ) : (
          <div className="space-y-4">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full border-2 border-dashed ${accent.border} ${accent.text}`}>
              <Upload className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>
              <p className="text-text-secondary text-sm mb-2">{subtitle}</p>
              <span className="text-xs text-text-tertiary">{acceptedFormats}</span>
            </div>
          </div>
        )}
      </div>
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-red-400 text-sm text-center mt-2"
        >
          {error}
        </motion.p>
      )}
    </motion.div>
  );
};

export default FileUploadZone;
