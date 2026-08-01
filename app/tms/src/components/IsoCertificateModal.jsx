import React from 'react';
import Modal from './Modal';
import { ShieldCheck, Award, Calendar, FileText, CheckCircle2 } from 'lucide-react';

export default function IsoCertificateModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <Modal title="ISO 9001:2015 Quality Management Certificate" isOpen={isOpen} onClose={onClose} maxWidth="560px">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Banner */}
        <div
          style={{
            background: 'linear-gradient(135deg, #1e40af, #173b6d)',
            color: '#ffffff',
            padding: '20px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Award size={28} />
          </div>
          <div>
            <div style={{ fontSize: '16px', fontWeight: '700' }}>ISO 9001:2015 Certified</div>
            <div style={{ fontSize: '12px', opacity: 0.85 }}>Quality Management Systems for Transport Operations</div>
          </div>
        </div>

        {/* Certificate Details Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="tms-card" style={{ padding: '12px 16px' }}>
            <div className="card-subtitle">Certificate Name</div>
            <div style={{ fontWeight: '600', fontSize: '13px', marginTop: '2px' }}>
              Accesco Living Quality Certificate
            </div>
          </div>

          <div className="tms-card" style={{ padding: '12px 16px' }}>
            <div className="card-subtitle">Certification Status</div>
            <div style={{ fontWeight: '700', fontSize: '13px', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
              <CheckCircle2 size={14} /> Active & Compliant
            </div>
          </div>

          <div className="tms-card" style={{ padding: '12px 16px' }}>
            <div className="card-subtitle">Issue Date</div>
            <div style={{ fontWeight: '600', fontSize: '13px', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Calendar size={14} /> 2025-01-15
            </div>
          </div>

          <div className="tms-card" style={{ padding: '12px 16px' }}>
            <div className="card-subtitle">Expiry Date</div>
            <div style={{ fontWeight: '600', fontSize: '13px', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Calendar size={14} /> 2028-01-14
            </div>
          </div>
        </div>

        {/* Scope Box */}
        <div className="tms-card" style={{ padding: '14px 16px' }}>
          <div className="card-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={14} /> Certification Scope
          </div>
          <p style={{ fontSize: '12px', color: 'var(--dark-text)', marginTop: '6px', lineHeight: '1.5' }}>
            "Provision of end-to-end transportation planning, carrier tender execution, automated freight auditing, IoT telematics tracking, and ERP integration controls for Accesco Living’s multi-hub furniture supply chain."
          </p>
        </div>

        {/* Footer buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
          <button className="tms-button tms-btn-primary" onClick={onClose}>
            Close Certificate
          </button>
        </div>
      </div>
    </Modal>
  );
}
