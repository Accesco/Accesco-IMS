import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import {
  TriangleAlert,
  CheckCircle2,
  Trash2,
  Search,
  Filter,
  Eye,
  BellOff
} from 'lucide-react';

export default function AlertsAndExceptions() {
  const { state, dispatch, showToast } = useTMS();
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('All');

  const filteredAlerts = (state.alerts || []).filter((a) => {
    const matchesSearch =
      a.message.toLowerCase().includes(search.toLowerCase()) ||
      a.type.toLowerCase().includes(search.toLowerCase()) ||
      a.shipmentId?.toLowerCase().includes(search.toLowerCase());

    const matchesSeverity = severityFilter === 'All' || a.severity === severityFilter;
    return matchesSearch && matchesSeverity;
  });

  const handleMarkRead = (alertId) => {
    dispatch({ type: 'MARK_ALERT_READ', payload: alertId });
    showToast('Alert marked as read', 'info');
  };

  const handleClearAlert = (alertId) => {
    dispatch({ type: 'CLEAR_ALERT', payload: alertId });
    showToast('Alert resolved and removed', 'success');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <TriangleAlert color="#ef4444" size={22} />
            Alerts & Exception Management Center
          </h2>
          <p className="card-subtitle">
            Centralised monitoring for live telematics excursions, SLA tender timeouts, capacity warnings & tariff variances.
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="tms-card" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--secondary-text)' }} />
          <input
            type="text"
            className="tms-input"
            style={{ width: '100%', paddingLeft: '36px' }}
            placeholder="Search alert message, shipment ID, exception type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select className="tms-select" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
          <option value="All">All Severities</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>

      {/* Alerts Table */}
      <div className="tms-table-container">
        <table className="tms-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Severity</th>
              <th>Exception Type</th>
              <th>Shipment Target</th>
              <th>Source Stream</th>
              <th>Description Message</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: 'var(--secondary-text)' }}>
                  No active exception alerts matching filter
                </td>
              </tr>
            ) : (
              filteredAlerts.map((a) => (
                <tr key={a.id} style={{ opacity: a.isRead ? 0.6 : 1 }}>
                  <td style={{ fontSize: '11px', fontWeight: '600', fontFamily: 'monospace' }}>
                    {a.timestamp}
                  </td>
                  <td>
                    <StatusBadge status={a.severity} />
                  </td>
                  <td style={{ fontWeight: '700', color: 'var(--dark-text)' }}>{a.type}</td>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{a.shipmentId || 'N/A'}</td>
                  <td style={{ fontSize: '11px' }}>{a.source}</td>
                  <td style={{ fontSize: '12px', maxWidth: '380px' }}>{a.message}</td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '4px' }}>
                      {!a.isRead && (
                        <button
                          className="tms-button tms-btn-secondary tms-btn-sm"
                          onClick={() => handleMarkRead(a.id)}
                          title="Mark as Read"
                        >
                          Mark Read
                        </button>
                      )}
                      <button
                        className="tms-button tms-btn-primary tms-btn-sm"
                        onClick={() => handleClearAlert(a.id)}
                        title="Resolve & Dismiss"
                      >
                        <CheckCircle2 size={12} /> Resolve
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
