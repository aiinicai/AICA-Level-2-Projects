import React from 'react';
import { createRoot } from 'react-dom/client';
import LitigationTracker from './LitigationTracker.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LitigationTracker />
  </React.StrictMode>
);
