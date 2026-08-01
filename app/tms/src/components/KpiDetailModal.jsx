import React from 'react';
import Modal from './Modal';
import Sparkline from './Sparkline';
import { useTMS } from '../context/TMSContext';
import { TrendingUp, ArrowRight, Layers } from 'lucide-react';

export default function KpiDetailModal({ kpiData, isOpen, onClose }) {
  const { dispatch } = useTMS();

  if (!isOpen || !kpiData) return null;

  const handleNavigateRelated = (route) => {
    dispatch({ type: 'SET_ROUTE', payload: route });
    onClose();
  };

  return (
    <Modal title={`Metric Breakdown: ${kpiData.title}`} isOpen={isOpen} onClose={onClose} maxWidth="580px">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Metric Header Card */}
        <div
          style={{
            padding: '18px',
            borderRadius: '12px',
            backgroundColor: `${kpiData.accentColor || '#2563eb'}12`,
            border: `1px solid ${kpiData.accentColor || '#2563eb'}30`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div className="card-subtitle" style={{ color: 'var(--secondary-text)' }}>Current Metric Value</div>
            <div style={{ fontSize: '32px', fontWeight: '800', color: 'var(--dark-text)', lineHeight: '1.1' }}>
              {kpiData.value}
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', color: kpiData.isPositive ? '#16a34a' : '#ef4444', marginTop: '4px' }}>
              {kpiData.changeText} vs Previous 30-Day Period
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div className="card-subtitle">7-Day Trend</div>
            <div style={{ marginTop: '8px' }}>
              <Sparkline data={kpiData.sparklineData || [30, 40, 50, 60, 55, 70, 80]} color={kpiData.accentColor || '#2563eb'} />
            </div>
          </div>
        </div>

        {/* Breakdown Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="tms-card" style={{ padding: '12px 16px' }}>
            <div className="card-subtitle">Previous Period Value</div>
            <div style={{ fontWeight: '700', fontSize: '16px', marginTop: '2px' }}>
              {kpiData.prevValue || '120'}
            </div>
          </div>

          <div className="tms-card" style={{ padding: '12px 16px' }}>
            <div className="card-subtitle">Period Performance Delta</div>
            <div style={{ fontWeight: '700', fontSize: '16px', color: '#16a34a', marginTop: '2px' }}>
              {kpiData.changeText || '+2.4%'}
            </div>
          </div>
        </div>

        {/* Definition Box */}
        <div className="tms-card" style={{ padding: '14px 16px' }}>
          <div className="card-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={14} /> Operational Definition & SLA Standard
          </div>
          <p style={{ fontSize: '12px', color: 'var(--dark-text)', marginTop: '6px', lineHeight: '1.4' }}>
            {kpiData.definition || kpiData.description}
          </p>
        </div>

        {/* Related Records Summary */}
        <div className="tms-card" style={{ padding: '14px 16px' }}>
          <div className="card-subtitle">Related Records Sample</div>
          <div style={{ fontSize: '12px', color: 'var(--dark-text)', marginTop: '6px' }}>
            {kpiData.relatedSummary || 'Connected with live order streams, carrier tendering waterfalls, and telemetry logs.'}
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
          <button className="tms-button tms-btn-secondary" onClick={onClose}>
            Close
          </button>
          <button
            className="tms-button tms-btn-primary"
            onClick={() => handleNavigateRelated(kpiData.targetRoute || '/')}
          >
            View Details <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </Modal>
  );
}
