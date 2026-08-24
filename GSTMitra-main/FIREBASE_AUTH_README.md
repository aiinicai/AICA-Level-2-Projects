# Firebase Authentication Integration

## Overview
This project now includes Firebase Authentication with email/password and Google login functionality. User UIDs are stored for database tracking.

## Features Implemented

### 🔐 Authentication Methods
- **Email/Password**: Traditional signup and login
- **Google OAuth**: One-click Google authentication
- **User Profile Management**: Display user information and logout

### 🗄️ Database Integration
- **Firestore Storage**: User data stored in Firestore with UID tracking
- **User Documents**: Each user gets a document in the `users` collection
- **Automatic Profile Creation**: User profiles created on first login

### 🎨 UI Components
- **AuthModal**: Modal for login/signup forms
- **LoginForm**: Email/password login with Google option
- **SignupForm**: User registration with validation
- **AuthHeader**: Header component with login/profile button
- **UserProfile**: Dropdown showing user info and logout
- **ProtectedRoute**: Component to protect routes requiring authentication

## File Structure

```
src/
├── firebase/
│   ├── config.js          # Firebase configuration
│   └── auth.js             # Authentication functions
├── contexts/
│   └── AuthContext.jsx    # React context for auth state
├── components/Auth/
│   ├── AuthModal.jsx      # Authentication modal
│   ├── LoginForm.jsx      # Login form component
│   ├── SignupForm.jsx     # Signup form component
│   ├── AuthHeader.jsx     # Header with auth controls
│   ├── UserProfile.jsx    # User profile dropdown
│   ├── ProtectedRoute.jsx # Route protection component
│   └── AuthDemo.jsx       # Demo component showing user data
```

## Usage Examples

### 1. Basic Authentication Context
```jsx
import { useAuth } from './contexts/AuthContext';

function MyComponent() {
  const { currentUser, userData, isAuthenticated, loading } = useAuth();
  
  if (loading) return <div>Loading...</div>;
  
  return (
    <div>
      {isAuthenticated ? (
        <p>Welcome, {userData?.displayName}!</p>
      ) : (
        <p>Please sign in</p>
      )}
    </div>
  );
}
```

### 2. Protected Routes
```jsx
import ProtectedRoute from './components/Auth/ProtectedRoute';

function App() {
  return (
    <ProtectedRoute>
      <SecureComponent />
    </ProtectedRoute>
  );
}
```

### 3. Manual Authentication
```jsx
import { signInWithEmail, signInWithGoogle, signOutUser } from './firebase/auth';

// Email login
const { user, error } = await signInWithEmail(email, password);

// Google login
const { user, error } = await signInWithGoogle();

// Logout
await signOutUser();
```

### 4. Getting User Data
```jsx
import { getCurrentUser, getUserData } from './firebase/auth';

// Get current user
const user = getCurrentUser();

// Get user data from Firestore
const { data, error } = await getUserData(user.uid);
```

## User Data Structure

Each user document in Firestore contains:
```javascript
{
  uid: "user_unique_id",
  email: "user@example.com",
  displayName: "User Name",
  photoURL: "https://...", // Only for Google users
  createdAt: "2024-01-01T00:00:00.000Z",
  provider: "email" | "google",
  usage_count: 0, // number
  is_paid: false, // boolean
  subscription_expiry: null, // timestamp
  upi_txn_id: "" // string
}
```

## Firebase Configuration

The Firebase configuration is already set up in `src/firebase/config.js` with your project credentials:
- Project ID: `gstmitra-316d9`
- Auth Domain: `gstmitra-316d9.firebaseapp.com`

## Security Features

1. **Client-side Validation**: Form validation before submission
2. **Firebase Security Rules**: Server-side validation (configure in Firebase Console)
3. **UID Tracking**: Each user action can be tracked by UID
4. **Secure Authentication**: Firebase handles password hashing and security

## Next Steps

1. **Configure Firebase Security Rules** in the Firebase Console
2. **Enable Google OAuth** in Firebase Authentication settings
3. **Customize UI** to match your app's design
4. **Add Role-based Access** if needed
5. **Implement Password Reset** functionality

## Firebase Console Setup Required

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `gstmitra-316d9`
3. Enable Authentication providers:
   - Email/Password ✅
   - Google ✅
4. Configure authorized domains for production
5. Set up Firestore security rules

## Environment Variables (Optional)

For production, consider moving Firebase config to environment variables:
```javascript
// .env
REACT_APP_FIREBASE_API_KEY=your_api_key
REACT_APP_FIREBASE_AUTH_DOMAIN=your_auth_domain
// ... other config
```

## Testing

Use the `AuthDemo` component to test authentication functionality:
```jsx
import AuthDemo from './components/Auth/AuthDemo';

// Add to any component to see user data
<AuthDemo />
```
