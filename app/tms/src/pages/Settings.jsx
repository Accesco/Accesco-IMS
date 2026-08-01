import React from 'react';
import { useTMS } from '../context/TMSContext';
import {
  Settings as SettingsIcon,
  RotateCw,
  Moon,
  Sun,
  DollarSign,
  Clock,
  Database,
  FileCheck2,
  Download
} from 'lucide-react';

export default function Settings() {
  const { state, dispatch, showToast } = useTMS();

  const handleToggleTheme = () => {
    dispatch({ type: 'TOGGLE_THEME' });
    showToast(`Switched theme to ${state.darkMode ? 'Light' : 'Dark'} mode`, 'info');
  };

  const handleResetDemoData = () => {
    dispatch({ type: 'RESET_DEMO_DATA' });
    showToast('Demo data successfully restored to pristine initial state!', 'success');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <SettingsIcon color="var(--primary-blue)" size={22} />
            System Configuration & Preferences
          </h2>
          <p className="card-subtitle">
            Global system parameters, currency, theme preferences, and demo state reset.
          </p>
        </div>
      </div>

      {/* Settings Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Appearance & Interface */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header-flex">
            <span className="card-title">Theme & Visual Experience</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', background: 'var(--bg-color)', borderRadius: '8px' }}>
            <div>
              <div style={{ fontWeight: '700', fontSize: '13px' }}>Color Theme</div>
              <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>
                Currently using {state.darkMode ? 'Dark Mode' : 'Light Mode'}
              </div>
            </div>

            <button className="tms-button tms-btn-secondary" onClick={handleToggleTheme}>
              {state.darkMode ? <Sun size={16} color="#f59e0b" /> : <Moon size={16} color="#8b5cf6" />}
              Toggle Theme
            </button>
          </div>
        </div>

        {/* Currency & Financial Configuration */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header-flex">
            <span className="card-title">Financial Currency Settings</span>
          </div>

          <div style={{ padding: '12px', background: 'var(--bg-color)', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className="card-subtitle">System Default Display Currency</div>
            <select
              className="tms-select"
              style={{ width: '100%' }}
              value={state.currency || 'SAR'}
              onChange={(e) => dispatch({ type: 'SET_CURRENCY', payload: e.target.value })}
            >
              <option value="SAR">SAR - Saudi Riyal (Default Enterprise)</option>
              <option value="INR">INR - Indian Rupee (₹)</option>
              <option value="USD">USD - US Dollar ($)</option>
            </select>
          </div>
        </div>

        {/* Enterprise Functional Audit PDF Report Card */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', gridColumn: 'span 2' }}>
          <div className="card-header-flex">
            <span className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileCheck2 size={18} color="var(--primary-blue)" />
              Enterprise Functional Audit & Architecture Document
            </span>
          </div>

          <div style={{ padding: '16px', background: 'var(--bg-color)', borderRadius: '10px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--dark-text)' }}>
                TMS Functional Audit & Feature Assessment Report (PDF)
              </div>
              <div style={{ fontSize: '12px', color: 'var(--secondary-text)', marginTop: '2px' }}>
                Complete software specification, module-by-module audit matrix, 13-stage workflow verification, state analysis, and production readiness evaluation.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <a
                href="/audit-report.html"
                target="_blank"
                rel="noopener noreferrer"
                className="tms-button tms-btn-secondary"
                style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <FileCheck2 size={16} /> Open Printable HTML
              </a>
              <a
                href="/TMS_Functional_Audit_Report.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="tms-button tms-btn-primary"
                style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <Download size={16} /> Download Report PDF
              </a>
            </div>
          </div>
        </div>

        {/* Demo State Reset Panel */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', gridColumn: 'span 2' }}>
          <div className="card-header-flex">
            <span className="card-title">Demo State Reset</span>
          </div>

          <div style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.06)', borderRadius: '10px', border: '1px solid rgba(239, 68, 68, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--dark-text)' }}>
                Restore Initial Demo Seed Data
              </div>
              <div style={{ fontSize: '12px', color: 'var(--secondary-text)', marginTop: '2px' }}>
                Resets all local storage state back to original sample orders, active shipments, carriers, and telemetry logs.
              </div>
            </div>

            <button className="tms-button tms-btn-outline-danger" onClick={handleResetDemoData}>
              <RotateCw size={16} /> Reset Demo Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
