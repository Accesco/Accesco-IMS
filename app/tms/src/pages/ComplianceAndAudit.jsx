import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import IsoCertificateModal from '../components/IsoCertificateModal';
import Pagination from '../components/Pagination';
import StatusBadge from '../components/StatusBadge';
import {
  ShieldCheck,
  Award,
  Search,
  Filter,
  FileText,
  Building2,
  CheckCircle2,
  AlertTriangle,
  History
} from 'lucide-react';

export default function ComplianceAndAudit() {
  const { state } = useTMS();
  const [isIsoModalOpen, setIsIsoModalOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [moduleFilter, setModuleFilter] = useState('All');
  const [severityFilter, setSeverityFilter] = useState('All');

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const filteredLogs = (state.auditLogs || []).filter((log) => {
    const matchesSearch =
      log.user.toLowerCase().includes(search.toLowerCase()) ||
      log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.recordId.toLowerCase().includes(search.toLowerCase());

    const matchesModule = moduleFilter === 'All' || log.module === moduleFilter;
    const matchesSeverity = severityFilter === 'All' || log.severity === severityFilter;

    return matchesSearch && matchesModule && matchesSeverity;
  });

  const totalPages = Math.ceil(filteredLogs.length / pageSize);
  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck color="var(--primary-blue)" size={22} />
            Governance, ISO 9001 & Audit Trail
          </h2>
          <p className="card-subtitle">
            Regulatory quality management standards, ISO certification scope, and immutable audit event ledger.
          </p>
        </div>

        <button className="tms-button tms-btn-primary" onClick={() => setIsIsoModalOpen(true)}>
          <Award size={16} /> View ISO 9001 Certificate
        </button>
      </div>

      {/* Compliance Standard Cards */}
      <div className="grid-4">
        {/* ISO Card */}
        <div className="tms-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary-blue)' }}>
            <Award size={20} />
            <span style={{ fontWeight: '700', fontSize: '14px' }}>ISO 9001:2015</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>Quality Management Systems</div>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#16a34a', marginTop: '4px' }}>
            Active & Certified
          </div>
        </div>

        {/* Carrier SLA Card */}
        <div className="tms-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#16a34a' }}>
            <Building2 size={20} />
            <span style={{ fontWeight: '700', fontSize: '14px' }}>Carrier SLA Matrix</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>Waterfall SLA Compliance</div>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#16a34a', marginTop: '4px' }}>
            98.2% Compliance Score
          </div>
        </div>

        {/* Fleet Asset Safety */}
        <div className="tms-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#8b5cf6' }}>
            <ShieldCheck size={20} />
            <span style={{ fontWeight: '700', fontSize: '14px' }}>Asset Fleet Safety</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>Inspection & Reefer Standards</div>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#16a34a', marginTop: '4px' }}>
            100% Vehicles Verified
          </div>
        </div>

        {/* Freight Audit Card */}
        <div className="tms-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#06b6d4' }}>
            <FileText size={20} />
            <span style={{ fontWeight: '700', fontSize: '14px' }}>Freight Financial Audit</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>3-Way Tariff Matching</div>
          <div style={{ fontSize: '12px', fontWeight: '700', color: '#16a34a', marginTop: '4px' }}>
            98.7% Pass Rate
          </div>
        </div>
      </div>

      {/* Audit Log Toolbar & Table */}
      <div className="tms-card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--secondary-text)' }} />
          <input
            type="text"
            className="tms-input"
            style={{ width: '100%', paddingLeft: '36px' }}
            placeholder="Search audit user, action, record ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select className="tms-select" value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)}>
          <option value="All">All Modules</option>
          <option value="ERP Order Intake">ERP Order Intake</option>
          <option value="Consolidation">Consolidation</option>
          <option value="Tender Waterfall">Tender Waterfall</option>
          <option value="Spot Auctions">Spot Auctions</option>
          <option value="Freight Audit">Freight Audit</option>
          <option value="System Settings">System Settings</option>
        </select>

        <select className="tms-select" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
          <option value="All">All Severities</option>
          <option value="Info">Info</option>
          <option value="Warning">Warning</option>
          <option value="Error">Error</option>
          <option value="Critical">Critical</option>
        </select>
      </div>

      {/* Audit Table */}
      <div className="tms-table-container">
        <table className="tms-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User / System Agent</th>
              <th>Module</th>
              <th>Action</th>
              <th>Record ID</th>
              <th>Previous Value</th>
              <th>New Value</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {paginatedLogs.map((log) => (
              <tr key={log.id}>
                <td style={{ fontSize: '11px', fontWeight: '600', fontFamily: 'monospace' }}>
                  {log.timestamp}
                </td>
                <td style={{ fontWeight: '600' }}>{log.user}</td>
                <td>{log.module}</td>
                <td style={{ fontWeight: '600', color: 'var(--dark-text)' }}>{log.action}</td>
                <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{log.recordId}</td>
                <td style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>{log.previousValue}</td>
                <td style={{ fontSize: '11px', fontWeight: '600' }}>{log.newValue}</td>
                <td>
                  <StatusBadge status={log.severity} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={filteredLogs.length}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />
      </div>

      {/* ISO Certificate Modal */}
      {isIsoModalOpen && (
        <IsoCertificateModal
          isOpen={isIsoModalOpen}
          onClose={() => setIsIsoModalOpen(false)}
        />
      )}
    </div>
  );
}
