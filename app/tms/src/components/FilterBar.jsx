import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import {
  RotateCw,
  Download,
  Calendar,
  FilterX
} from 'lucide-react';
import styles from '../styles/dashboard.module.css';
import Modal from './Modal';

export default function FilterBar() {
  const { state, dispatch, showToast } = useTMS();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isCustomDateModalOpen, setIsCustomDateModalOpen] = useState(false);
  const [customStart, setCustomStart] = useState('2026-07-01');
  const [customEnd, setCustomEnd] = useState('2026-07-28');

  const { filters } = state;

  const handleFilterChange = (key, value) => {
    if (key === 'dateRange' && value === 'Custom Range') {
      setIsCustomDateModalOpen(true);
    } else {
      dispatch({ type: 'SET_FILTERS', payload: { [key]: value } });
    }
  };

  const handleApplyCustomDate = () => {
    dispatch({
      type: 'SET_FILTERS',
      payload: { dateRange: `Custom (${customStart} to ${customEnd})` },
    });
    setIsCustomDateModalOpen(false);
    showToast(`Applied custom date range: ${customStart} to ${customEnd}`, 'info');
  };

  const handleResetFilters = () => {
    dispatch({ type: 'RESET_FILTERS' });
    showToast('Filters reset to default', 'info');
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      dispatch({ type: 'REFRESH_DASHBOARD' });
      setIsRefreshing(false);
      showToast('Dashboard metrics refreshed live from event stream', 'success');
    }, 1000);
  };

  const handleExportCSV = () => {
    // Generate CSV content of filtered shipments and KPIs
    const headers = [
      'Shipment ID',
      'Type',
      'Origin',
      'Destination Zone',
      'Weight (kg)',
      'Volume (Cbm)',
      'Carrier',
      'Procurement Status',
      'Shipment Status',
      'ETA',
      'Cost (SAR)',
    ];

    const rows = state.shipments.map((s) => [
      s.id,
      s.shipmentType,
      `"${s.origin}"`,
      s.destinationZone,
      s.totalWeightKg,
      s.totalVolumeCbm,
      `"${s.carrierName || 'Unassigned'}"`,
      s.procurementStatus,
      s.shipmentStatus,
      s.eta,
      s.costSAR || 0,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Accesco_TMS_Export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast('Exported TMS dataset as CSV', 'success');
  };

  return (
    <div className={styles.filterBarContainer}>
      <div className={styles.filterBarScroll}>
        {/* Date Range */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Date Range</label>
          <select
            className="tms-select"
            value={filters.dateRange}
            onChange={(e) => handleFilterChange('dateRange', e.target.value)}
          >
            <option value="Last 7 Days">Last 7 Days</option>
            <option value="Last 30 Days">Last 30 Days</option>
            <option value="Last 90 Days">Last 90 Days</option>
            <option value="This Year">This Year</option>
            <option value="Custom Range">Custom Range...</option>
          </select>
        </div>

        {/* Origin Complex */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Origin Complex</label>
          <select
            className="tms-select"
            value={filters.originComplex}
            onChange={(e) => handleFilterChange('originComplex', e.target.value)}
          >
            <option value="All Origin Complexes">All Origin Complexes</option>
            <option value="BGL-CENTRAL">Bengaluru Central Hub</option>
            <option value="BGL-NORTH">Bengaluru North Hub</option>
            <option value="HYD-HUB">Hyderabad Hub</option>
            <option value="CHN-HUB">Chennai Hub</option>
            <option value="MUM-HUB">Mumbai Hub</option>
          </select>
        </div>

        {/* Destination Zone */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Destination Zone</label>
          <select
            className="tms-select"
            value={filters.destinationZone}
            onChange={(e) => handleFilterChange('destinationZone', e.target.value)}
          >
            <option value="All Zones">All Zones</option>
            <option value="North Zone">North Zone</option>
            <option value="South Zone">South Zone</option>
            <option value="East Zone">East Zone</option>
            <option value="West Zone">West Zone</option>
            <option value="Central Zone">Central Zone</option>
          </select>
        </div>

        {/* Carrier */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Carrier</label>
          <select
            className="tms-select"
            value={filters.carrier}
            onChange={(e) => handleFilterChange('carrier', e.target.value)}
          >
            <option value="All Carriers">All Carriers</option>
            {state.carriers.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {/* Shipment Status */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Shipment Status</label>
          <select
            className="tms-select"
            value={filters.shipmentStatus}
            onChange={(e) => handleFilterChange('shipmentStatus', e.target.value)}
          >
            <option value="All Statuses">All Statuses</option>
            <option value="Unallocated">Unallocated</option>
            <option value="Consolidating">Consolidating</option>
            <option value="Planned">Planned</option>
            <option value="Tendering">Tendering</option>
            <option value="Carrier Assigned">Carrier Assigned</option>
            <option value="In Transit">In Transit</option>
            <option value="Delivered">Delivered</option>
            <option value="Exception">Exception</option>
            <option value="Cancelled">Cancelled</option>
          </select>
        </div>

        {/* Transport Mode */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Transport Mode</label>
          <select
            className="tms-select"
            value={filters.transportMode}
            onChange={(e) => handleFilterChange('transportMode', e.target.value)}
          >
            <option value="All Modes">All Modes</option>
            <option value="LTL">LTL</option>
            <option value="FTL">FTL</option>
            <option value="Milk Run">Milk Run</option>
            <option value="Dedicated Vehicle">Dedicated Vehicle</option>
            <option value="Reefer">Reefer</option>
          </select>
        </div>

        {/* Procurement Status */}
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Procurement Status</label>
          <select
            className="tms-select"
            value={filters.procurementStatus}
            onChange={(e) => handleFilterChange('procurementStatus', e.target.value)}
          >
            <option value="All Procurement Statuses">All Procurement Statuses</option>
            <option value="Contract Matching">Contract Matching</option>
            <option value="Tender Dispatched">Tender Dispatched</option>
            <option value="Awaiting Response">Awaiting Response</option>
            <option value="Accepted">Accepted</option>
            <option value="Rejected">Rejected</option>
            <option value="Timed Out">Timed Out</option>
            <option value="Spot Auction">Spot Auction</option>
            <option value="Human Dispatch">Human Dispatch</option>
          </select>
        </div>

        {/* Filter Action Buttons */}
        <div className={styles.filterActions}>
          <button
            className="tms-button tms-btn-secondary tms-btn-sm"
            onClick={handleResetFilters}
            title="Reset Filters"
          >
            <FilterX size={14} />
            Reset
          </button>

          <button
            className="tms-button tms-btn-secondary tms-btn-sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            title="Refresh metrics live"
          >
            <RotateCw size={14} className={isRefreshing ? styles.spin : ''} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>

          <button
            className="tms-button tms-btn-primary tms-btn-sm"
            onClick={handleExportCSV}
            title="Export CSV"
          >
            <Download size={14} />
            Export
          </button>
        </div>
      </div>

      {/* Blueprint Status Subtitle */}
      <div className={styles.filterSubtitle}>
        Accesco Living TMS · Enterprise transport overview · Live simulation (Refreshed at{' '}
        {state.lastRefreshed})
      </div>

      {/* Custom Date Range Modal */}
      {isCustomDateModalOpen && (
        <Modal
          title="Select Custom Date Range"
          isOpen={isCustomDateModalOpen}
          onClose={() => setIsCustomDateModalOpen(false)}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <label className="card-subtitle">Start Date</label>
                <input
                  type="date"
                  className="tms-input"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label className="card-subtitle">End Date</label>
                <input
                  type="date"
                  className="tms-input"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button
                className="tms-button tms-btn-secondary"
                onClick={() => setIsCustomDateModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="tms-button tms-btn-primary"
                onClick={handleApplyCustomDate}
              >
                Apply Range
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
