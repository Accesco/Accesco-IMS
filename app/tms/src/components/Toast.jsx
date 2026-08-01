import React, { useEffect } from 'react';
import { useTMS } from '../context/TMSContext';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import styles from '../styles/components.module.css';

export default function Toast() {
  const { state, hideToast } = useTMS();
  const toast = state.toast;

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        hideToast();
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast, hideToast]);

  if (!toast) return null;

  const icons = {
    success: <CheckCircle2 size={18} color="#16a34a" />,
    warning: <AlertTriangle size={18} color="#f59e0b" />,
    error: <AlertCircle size={18} color="#ef4444" />,
    info: <Info size={18} color="#2563eb" />,
  };

  return (
    <div className={`${styles.toastContainer} ${styles[`toast_${toast.type || 'success'}`]}`}>
      <div className={styles.toastIcon}>{icons[toast.type] || icons.success}</div>
      <div className={styles.toastMsg}>{toast.message}</div>
      <button className={styles.toastCloseBtn} onClick={hideToast} aria-label="Dismiss toast">
        <X size={14} />
      </button>
    </div>
  );
}
