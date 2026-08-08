import React from 'react';
import { TMSProvider } from './context/TMSContext';
import AppContent from './AppContent';

export default function App() {
  return (
    <TMSProvider>
      <AppContent />
    </TMSProvider>
  );
}
