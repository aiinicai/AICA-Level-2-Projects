import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { storage } from './config';

/**
 * Uploads a profile image for a user and returns the download URL.
 * @param {File} file - The image file to upload.
 * @param {string} userId - The user's UID.
 * @returns {Promise<string>} - The public URL of the uploaded image.
 */
export const uploadProfileImage = async (file, userId) => {
  const storageRef = ref(storage, `profile-images/${userId}`);
  await uploadBytes(storageRef, file);
  const downloadURL = await getDownloadURL(storageRef);
  return downloadURL;
};
