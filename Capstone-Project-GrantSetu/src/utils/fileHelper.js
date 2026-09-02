/**
 * Utility functions for client-side document uploads, preview, and download
 */

// Convert File object to Base64 Data URL for persistent offline storage
export const readFileAsBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({
      id: `DOC-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      name: file.name,
      size: formatFileSize(file.size),
      type: file.type,
      dataUrl: reader.result,
      uploadedAt: new Date().toISOString()
    });
    reader.onerror = (error) => reject(error);
    reader.readAsDataURL(file);
  });
};

// Format File Size
export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

// Trigger browser file download from Data URL
export const downloadBase64File = (dataUrl, fileName) => {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = fileName || 'download';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
