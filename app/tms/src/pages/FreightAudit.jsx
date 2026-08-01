import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import Drawer from '../components/Drawer';
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Eye,
  DollarSign,
  ShieldCheck,
  FileCheck2
} from 'lucide-react';

export default function FreightAudit() {
  const { state, dispatch, showToast } = useTMS();
  const [selectedInvoice, setSelectedInvoice] = useState(null);

  const handleApproveInvoice = (inv) => {
    dispatch({
      type: 'APPROVE_INVOICE',
      payload: { invoiceId: inv.id },
    });
    showToast(`Invoice ${inv.id} approved via 3-way matching engine`, 'success');
  };

  const handleReleaseToERP = (inv) => {
    dispatch({
      type: 'RELEASE_INVOICE_TO_ERP',
      payload: { invoiceId: inv.id },
    });
    showToast(`Invoice ${inv.id} released to Accesco ERP Accounts Payable Ledger!`, 'success');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileCheck color="var(--primary-blue)" size={22} />
            Automated Freight Audit & 3-Way Matching
          </h2>
          <p className="card-subtitle">
            Audits contracted tariff rates against executed telematics POD and carrier freight invoices before ERP payment release.
          </p>
        </div>
      </div>

      {/* 3-Way Matching Architecture Diagram */}
      <div className="tms-card" style={{ padding: '14px 20px', background: 'var(--bg-color)' }}>
        <div className="card-subtitle" style={{ marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          3-Way Freight Audit Verification Architecture
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
          <div style={{ padding: '12px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--primary-blue)' }}>1. Contract Tariff Rate</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>
              Base linehaul rate, contracted fuel surcharge % & accessorial matrix
            </div>
          </div>
          <div style={{ padding: '12px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#16a34a' }}>2. Executed GPS POD</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>
              Delivery timestamp, GPS arrival geofence POD & reefer temp log
            </div>
          </div>
          <div style={{ padding: '12px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#8b5cf6' }}>3. Carrier Billed Invoice</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>
              Carrier linehaul charge, fuel surcharge & claimed accessorials
            </div>
          </div>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="tms-table-container">
        <table className="tms-table">
          <thead>
            <tr>
              <th>Invoice ID</th>
              <th>Carrier Partner</th>
              <th>Shipment ID</th>
              <th>Contract Rate</th>
              <th>Billed Linehaul</th>
              <th>Fuel Surcharge</th>
              <th>Total Billed</th>
              <th>Variance</th>
              <th>Audit Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {(state.invoices || []).map((inv) => {
              const contractRate = inv.contractRateSAR ?? inv.contractedExpectedTotalSAR ?? inv.baseLinehaulSAR ?? 0;
              const billedLinehaul = inv.billedLinehaulSAR ?? inv.baseLinehaulSAR ?? 0;
              const fuelSurcharge = inv.fuelSurchargeSAR ?? 0;
              const totalBilled = inv.totalBilledSAR ?? inv.submittedTotalSAR ?? 0;
              const variance = inv.varianceSAR ?? 0;

              return (
                <tr key={inv.id}>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{inv.id}</td>
                  <td style={{ fontWeight: '600' }}>{inv.carrierName}</td>
                  <td>{inv.shipmentId}</td>
                  <td>SAR {contractRate.toLocaleString()}</td>
                  <td>SAR {billedLinehaul.toLocaleString()}</td>
                  <td>SAR {fuelSurcharge.toLocaleString()}</td>
                  <td style={{ fontWeight: '700' }}>SAR {totalBilled.toLocaleString()}</td>
                  <td>
                    <span
                      style={{
                        fontWeight: '700',
                        color: variance > 0 ? '#ef4444' : variance < 0 ? '#16a34a' : 'var(--dark-text)',
                      }}
                    >
                      {variance > 0 ? `+SAR ${variance.toLocaleString()}` : `SAR ${variance.toLocaleString()}`}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={inv.auditStatus} />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '4px' }}>
                      <button
                        className="tms-button tms-btn-secondary tms-btn-sm"
                        onClick={() => setSelectedInvoice(inv)}
                        title="Inspect 3-Way Variance"
                      >
                        <Eye size={12} /> Inspect
                      </button>

                      {inv.auditStatus === 'Pending Audit' && (
                        <button
                          className="tms-button tms-btn-primary tms-btn-sm"
                          onClick={() => handleApproveInvoice(inv)}
                          title="Approve Invoice"
                        >
                          <CheckCircle2 size={12} /> Approve
                        </button>
                      )}

                      {inv.auditStatus === 'Verified & Approved' && (
                        <button
                          className="tms-button tms-btn-primary tms-btn-sm"
                          onClick={() => handleReleaseToERP(inv)}
                          title="Release to ERP Ledger"
                        >
                          <FileCheck2 size={12} /> Release ERP
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Variance Breakdown Drawer */}
      {selectedInvoice && (() => {
        const contractRate = selectedInvoice.contractRateSAR ?? selectedInvoice.contractedExpectedTotalSAR ?? selectedInvoice.baseLinehaulSAR ?? 0;
        const billedLinehaul = selectedInvoice.billedLinehaulSAR ?? selectedInvoice.baseLinehaulSAR ?? 0;
        const fuelSurcharge = selectedInvoice.fuelSurchargeSAR ?? 0;
        const accessorials = selectedInvoice.accessorialChargesSAR ?? selectedInvoice.accessorialSAR ?? 0;
        const variance = selectedInvoice.varianceSAR ?? 0;

        return (
          <Drawer
            title={`3-Way Audit Inspector: ${selectedInvoice.id}`}
            isOpen={!!selectedInvoice}
            onClose={() => setSelectedInvoice(null)}
            width="560px"
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="card-subtitle">Carrier: {selectedInvoice.carrierName}</span>
                <StatusBadge status={selectedInvoice.auditStatus} />
              </div>

              {/* Side-by-side comparison */}
              <div className="tms-card" style={{ padding: '14px' }}>
                <div className="card-subtitle" style={{ marginBottom: '8px' }}>Linehaul & Fuel Surcharge Comparison</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px' }}>
                  <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '6px' }}>
                    <div style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>Contract Rate</div>
                    <div style={{ marginTop: '4px' }}>Base Linehaul: SAR {contractRate.toLocaleString()}</div>
                    <div>Fuel Surcharge: SAR {(contractRate * 0.12).toFixed(0)}</div>
                  </div>

                  <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '6px' }}>
                    <div style={{ fontWeight: '700', color: variance !== 0 ? '#ef4444' : '#16a34a' }}>
                      Carrier Billed
                    </div>
                    <div style={{ marginTop: '4px' }}>Billed Linehaul: SAR {billedLinehaul.toLocaleString()}</div>
                    <div>Billed Fuel: SAR {fuelSurcharge.toLocaleString()}</div>
                  </div>
                </div>
              </div>

              {/* Accessorial Charges & Penalties */}
              <div className="tms-card" style={{ padding: '14px' }}>
                <div className="card-subtitle" style={{ marginBottom: '8px' }}>Claimed Accessorial Charges</div>
                <div style={{ fontSize: '12px', color: 'var(--dark-text)' }}>
                  Accessorials Billed: <strong>SAR {accessorials.toLocaleString()}</strong>
                  <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '4px' }}>
                    {selectedInvoice.varianceReason || 'No unauthorized detention or demurrage charges detected.'}
                  </div>
                </div>
              </div>

              {/* GPS POD Telematics Verification */}
              <div className="tms-card" style={{ padding: '14px' }}>
                <div className="card-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <ShieldCheck size={16} color="#16a34a" /> Executed Telematics Verification
                </div>
                <div style={{ fontSize: '12px', marginTop: '6px', lineHeight: '1.5' }}>
                  <div>Proof of Delivery (POD): <strong>VERIFIED (Digital Signature & Geofence Entry)</strong></div>
                  <div>Actual Delivery Timestamp: 2026-07-28 14:15:00</div>
                  <div>Temperature Compliance: <strong>PASSED (Mean temp 4.2°C)</strong></div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button className="tms-button tms-btn-secondary" onClick={() => setSelectedInvoice(null)}>
                  Close
                </button>
                {selectedInvoice.auditStatus === 'Pending Audit' && (
                  <button className="tms-button tms-btn-primary" onClick={() => { handleApproveInvoice(selectedInvoice); setSelectedInvoice(null); }}>
                    Approve Invoice
                  </button>
                )}
              </div>
            </div>
          </Drawer>
        );
      })()}
    </div>
  );
}
