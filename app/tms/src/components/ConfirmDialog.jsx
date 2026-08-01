import React from 'react';
import Modal from './Modal';
import { AlertTriangle } from 'lucide-react';

export default function ConfirmDialog({
  isOpen,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed with this action?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDanger = false,
  onConfirm,
  onClose,
}) {
  if (!isOpen) return null;

  return (
    <Modal title={title} isOpen={isOpen} onClose={onClose} maxWidth="420px">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: '8px',
              backgroundColor: isDanger ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)',
              color: isDanger ? '#ef4444' : '#f59e0b',
            }}
          >
            <AlertTriangle size={20} />
          </div>
          <p style={{ fontSize: '13px', color: 'var(--dark-text)', lineHeight: '1.4' }}>
            {message}
          </p>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
          <button className="tms-button tms-btn-secondary" onClick={onClose}>
            {cancelText}
          </button>
          <button
            className={`tms-button ${isDanger ? 'tms-btn-danger' : 'tms-btn-primary'}`}
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
}
