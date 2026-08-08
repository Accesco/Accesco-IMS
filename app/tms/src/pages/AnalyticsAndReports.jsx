import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import {
  BarChart2,
  Download,
  Printer,
  Calendar,
  Filter,
  TrendingUp,
  Boxes,
  Gauge,
  Handshake,
  FileCheck
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

export default function AnalyticsAndReports() {
  const { state, showToast } = useTMS();
  const [timeframe, setTimeframe] = useState('Last 30 Days');

  // Chart data
  const volumeData = [
    { week: 'W1', TotalOrders: 420, ConsolidatedRuns: 340, SoloLTL: 80 },
    { week: 'W2', TotalOrders: 480, ConsolidatedRuns: 395, SoloLTL: 85 },
    { week: 'W3', TotalOrders: 510, ConsolidatedRuns: 425, SoloLTL: 85 },
    { week: 'W4', TotalOrders: 547, ConsolidatedRuns: 456, SoloLTL: 91 },
  ];

  const carrierComplianceData = [
    { carrier: 'Accesco Exp', OnTime: 98.4, Acceptance: 94.2 },
    { carrier: 'Safexpress', OnTime: 97.1, Acceptance: 92.0 },
    { carrier: 'Rivigo Cold', OnTime: 96.5, Acceptance: 91.5 },
    { carrier: 'VRL Freight', OnTime: 94.2, Acceptance: 89.0 },
    { carrier: 'GATI KWE', OnTime: 91.0, Acceptance: 84.5 },
  ];

  const spotSavingsData = [
    { auction: 'AUC-501', ReservePrice: 13000, AwardedPrice: 11500, Savings: 1500 },
    { auction: 'AUC-502', ReservePrice: 9500, AwardedPrice: 8400, Savings: 1100 },
    { auction: 'AUC-503', ReservePrice: 15000, AwardedPrice: 13200, Savings: 1800 },
    { auction: 'AUC-504', ReservePrice: 11000, AwardedPrice: 9800, Savings: 1200 },
  ];

  const handleExportCSV = () => {
    showToast('Exported TMS Analytics & Performance Report as CSV file', 'success');
  };

  const handlePrintReport = () => {
    window.print();
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BarChart2 color="var(--primary-blue)" size={22} />
            Enterprise Analytics & Intelligence Suite
          </h2>
          <p className="card-subtitle">
            Executive control tower reporting across order volume, consolidation density, carrier SLAs, and spot auction savings.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="tms-button tms-btn-secondary" onClick={handlePrintReport}>
            <Printer size={16} /> Print Executive Summary
          </button>
          <button className="tms-button tms-btn-primary" onClick={handleExportCSV}>
            <Download size={16} /> Export CSV
          </button>
        </div>
      </div>

      {/* Primary Analytics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Consolidation Efficiency Trend */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="card-header-flex">
            <span className="card-title">Order Consolidation Density (LTL to FTL)</span>
          </div>

          <div style={{ height: '260px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={volumeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="week" stroke="var(--secondary-text)" fontSize={11} />
                <YAxis stroke="var(--secondary-text)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card-bg)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="ConsolidatedRuns" fill="#2563eb" name="Consolidated Runs" radius={[4, 4, 0, 0]} />
                <Bar dataKey="SoloLTL" fill="#f59e0b" name="Solo LTL" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Carrier SLA & Acceptance Leaderboard */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="card-header-flex">
            <span className="card-title">Carrier On-Time SLA & Tender Acceptance</span>
          </div>

          <div style={{ height: '260px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={carrierComplianceData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis type="number" domain={[70, 100]} stroke="var(--secondary-text)" fontSize={11} />
                <YAxis dataKey="carrier" type="category" stroke="var(--secondary-text)" fontSize={11} width={100} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card-bg)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="OnTime" fill="#16a34a" name="On-Time Delivery %" radius={[0, 4, 4, 0]} />
                <Bar dataKey="Acceptance" fill="#06b6d4" name="Tender Acceptance %" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Reverse Spot Auction Procurement Savings */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="card-header-flex">
            <span className="card-title">Reverse Spot Auction Procurement Savings (SAR)</span>
          </div>

          <div style={{ height: '260px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={spotSavingsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="auction" stroke="var(--secondary-text)" fontSize={11} />
                <YAxis stroke="var(--secondary-text)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card-bg)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Area type="monotone" dataKey="ReservePrice" stroke="#6b7280" fill="rgba(107, 114, 128, 0.2)" name="Reserve Cap" />
                <Area type="monotone" dataKey="AwardedPrice" stroke="#16a34a" fill="rgba(22, 163, 74, 0.3)" name="Awarded Price" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Freight Audit Variance Summary */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="card-header-flex">
            <span className="card-title">Freight Audit 3-Way Pass Rate Summary</span>
          </div>

          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ padding: '16px', background: 'rgba(22, 163, 74, 0.1)', borderRadius: '10px', border: '1px solid #16a34a' }}>
                <div className="card-subtitle" style={{ color: '#16a34a' }}>Zero Variance Pass Rate</div>
                <div style={{ fontSize: '28px', fontWeight: '800', color: '#16a34a', marginTop: '4px' }}>98.7%</div>
                <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>Verified & released automatically</div>
              </div>

              <div style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '10px', border: '1px solid #ef4444' }}>
                <div className="card-subtitle" style={{ color: '#ef4444' }}>Billed Discrepancies</div>
                <div style={{ fontSize: '28px', fontWeight: '800', color: '#ef4444', marginTop: '4px' }}>1.3%</div>
                <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>Prevented SAR 42,500 overbilling</div>
              </div>
            </div>

            <div style={{ padding: '12px', background: 'var(--bg-color)', borderRadius: '8px', fontSize: '12px', color: 'var(--dark-text)' }}>
              <strong>Control Tower Audit Note:</strong> The 3-way automated matching engine automatically caught 4 linehaul surcharge over-claims across 180 invoices this month.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
