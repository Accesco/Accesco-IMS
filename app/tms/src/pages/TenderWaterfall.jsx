import React, { useState, useEffect } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import {
  Workflow,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Gavel,
  ArrowRight,
  ShieldAlert,
  Award
} from 'lucide-react';

export default function TenderWaterfall() {
  const { state, dispatch, showToast } = useTMS();
  const [selectedTenderId, setSelectedTenderId] = useState(state.tenders[0]?.id || 'TND-901');

  const activeTenders = state.tenders.filter((t) => t.status === 'Active');
  const selectedTender = state.tenders.find((t) => t.id === selectedTenderId) || state.tenders[0];

  // Simulation timer tick effect
  const [simTimer, setSimTimer] = useState(60);

  useEffect(() => {
    if (selectedTender && selectedTender.status === 'Active') {
      const interval = setInterval(() => {
        setSimTimer((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [selectedTender]);

  // Handle Simulate Accept
  const handleSimulateAccept = (tender) => {
    dispatch({
      type: 'TENDER_ACCEPT',
      payload: { tenderId: tender.id },
    });
    showToast(`Tender Accepted by ${tender.carrierName}! Shipment ${tender.shipmentId} assigned.`, 'success');
  };

  // Handle Simulate Reject
  const handleSimulateReject = (tender) => {
    dispatch({
      type: 'TENDER_REJECT',
      payload: { tenderId: tender.id, reason: 'Carrier capacity constraint on lane' },
    });
    showToast(`Tender Rejected by ${tender.carrierName}. Advancing to Rank 2 carrier...`, 'warning');
  };

  // Handle Simulate Timeout (Mandatory 2.5% penalty rule)
  const handleSimulateTimeout = (tender) => {
    dispatch({
      type: 'TENDER_TIMEOUT',
      payload: { tenderId: tender.id },
    });
    showToast(
      `Tender Timed Out for ${tender.carrierName}! 2.5% performance penalty applied to carrier tier score.`,
      'error'
    );
  };

  // Handle Create Spot Auction
  const handleSendToSpotAuction = (shipmentId) => {
    const auctionId = `AUC-${Math.floor(500 + Math.random() * 500)}`;
    const newAuction = {
      id: auctionId,
      shipmentId,
      status: 'Bidding',
      timeRemainingSecs: 90,
      origin: 'Bengaluru Central Hub',
      destinationZone: 'North Zone',
      destinationName: 'Delhi-NCR Mega Terminal',
      weightKg: 17800,
      volumeCbm: 58.5,
      reservePriceSAR: 13000,
      currentLowestBidSAR: null,
      lowestBidderCarrierName: null,
      totalBidsCount: 0,
    };

    dispatch({
      type: 'CREATE_SPOT_AUCTION',
      payload: { auction: newAuction },
    });

    dispatch({ type: 'SET_ROUTE', payload: '/spot-auctions' });
    showToast(`Created Reverse Spot Auction ${auctionId} for Shipment ${shipmentId}`, 'info');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Workflow color="var(--primary-blue)" size={22} />
            Automated Sequential Tender Waterfall
          </h2>
          <p className="card-subtitle">
            Ranks contracted carriers by cost & compliance score. 60-min SLA timer triggers mandatory -2.5% tier penalties on timeout.
          </p>
        </div>
      </div>

      {/* Visual State Machine Diagram */}
      <div className="tms-card" style={{ padding: '16px 20px', background: 'var(--bg-color)' }}>
        <div className="card-subtitle" style={{ marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Tender Dispatch Lifecycle State Machine
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px', textAlign: 'center', fontSize: '11px', fontWeight: '700' }}>
          <div style={{ padding: '8px', background: 'var(--card-bg)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            1. Planned
          </div>
          <div style={{ padding: '8px', background: 'var(--card-bg)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            2. Contracts Ranked
          </div>
          <div style={{ padding: '8px', background: '#2563eb', color: '#ffffff', borderRadius: '6px' }}>
            3. Rank 1 Tendered
          </div>
          <div style={{ padding: '8px', background: 'var(--card-bg)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            4. 60-Min SLA Timer
          </div>
          <div style={{ padding: '8px', background: '#16a34a', color: '#ffffff', borderRadius: '6px' }}>
            5A. Accepted
          </div>
          <div style={{ padding: '8px', background: '#ef4444', color: '#ffffff', borderRadius: '6px' }}>
            5B. Timeout (-2.5%)
          </div>
          <div style={{ padding: '8px', background: '#8b5cf6', color: '#ffffff', borderRadius: '6px' }}>
            6. Spot Auction
          </div>
        </div>
      </div>

      {/* Tender Workspace: Left Table, Right Inspection & Simulation */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '20px' }}>
        {/* Active & Historical Tenders Table */}
        <div className="tms-table-container">
          <table className="tms-table">
            <thead>
              <tr>
                <th>Tender ID</th>
                <th>Shipment ID</th>
                <th>Carrier</th>
                <th>Rank</th>
                <th>Contracted Rate</th>
                <th>Dispatch Time</th>
                <th>Response</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {state.tenders.map((t) => (
                <tr
                  key={t.id}
                  style={{
                    backgroundColor: selectedTender?.id === t.id ? 'rgba(37, 99, 235, 0.05)' : 'transparent',
                    cursor: 'pointer',
                  }}
                  onClick={() => setSelectedTenderId(t.id)}
                >
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{t.id}</td>
                  <td style={{ fontWeight: '600' }}>{t.shipmentId}</td>
                  <td>{t.carrierName}</td>
                  <td>
                    <span style={{ fontWeight: '700', padding: '2px 6px', background: 'rgba(0,0,0,0.06)', borderRadius: '4px' }}>
                      Rank {t.rank}
                    </span>
                  </td>
                  <td style={{ fontWeight: '700' }}>SAR {t.contractedRateSAR.toLocaleString()}</td>
                  <td style={{ fontSize: '11px' }}>{t.dispatchTime.split('T')[1]}</td>
                  <td>
                    <StatusBadge status={t.response} />
                  </td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="tms-button tms-btn-secondary tms-btn-sm"
                      onClick={() => setSelectedTenderId(t.id)}
                    >
                      Select
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Right Panel: Active Tender Simulation Control Box */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header-flex">
            <span className="card-title">Tender Simulation Controller</span>
          </div>

          {selectedTender ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ padding: '14px', background: 'var(--bg-color)', borderRadius: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="card-subtitle">Active Carrier Target</span>
                  <StatusBadge status={selectedTender.response} />
                </div>
                <div style={{ fontSize: '16px', fontWeight: '800', color: 'var(--dark-text)' }}>
                  {selectedTender.carrierName} (Rank {selectedTender.rank})
                </div>
                <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>
                  Contract Linehaul Rate: <strong>SAR {selectedTender.contractedRateSAR.toLocaleString()}</strong>
                </div>
              </div>

              {/* Simulation SLA Timer */}
              <div
                style={{
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid #f59e0b',
                  background: 'rgba(245, 158, 11, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontSize: '11px', fontWeight: '700', color: '#d97706', textTransform: 'uppercase' }}>
                    Simulation Waterfall Timer
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: '800', color: '#d97706', fontFamily: 'monospace' }}>
                    00:{simTimer < 10 ? `0${simTimer}` : simTimer} <span style={{ fontSize: '11px', fontWeight: '600' }}>(Business SLA: 60:00)</span>
                  </div>
                </div>
                <Clock size={28} color="#f59e0b" />
              </div>

              {/* Simulation Action Triggers */}
              {selectedTender.status === 'Active' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button
                    className="tms-button tms-btn-primary"
                    style={{ height: '38px', width: '100%' }}
                    onClick={() => handleSimulateAccept(selectedTender)}
                  >
                    <CheckCircle2 size={16} /> Simulate Carrier Accept
                  </button>

                  <button
                    className="tms-button tms-btn-secondary"
                    style={{ height: '38px', width: '100%' }}
                    onClick={() => handleSimulateReject(selectedTender)}
                  >
                    <XCircle size={16} color="#ef4444" /> Simulate Carrier Reject
                  </button>

                  <button
                    className="tms-button tms-btn-outline-danger"
                    style={{ height: '38px', width: '100%' }}
                    onClick={() => handleSimulateTimeout(selectedTender)}
                  >
                    <AlertTriangle size={16} /> Force 60-Min Timeout (-2.5% Penalty)
                  </button>
                </div>
              )}

              {/* Spot Auction Fallback Trigger */}
              <div style={{ borderTop: '1px dashed var(--border-color)', paddingTop: '12px', marginTop: '8px' }}>
                <div className="card-subtitle" style={{ marginBottom: '8px' }}>No Contract Carriers Available?</div>
                <button
                  className="tms-button tms-btn-secondary"
                  style={{ width: '100%', height: '36px' }}
                  onClick={() => handleSendToSpotAuction(selectedTender.shipmentId)}
                >
                  <Gavel size={14} color="#8b5cf6" /> Send to Reverse Spot Auction
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--secondary-text)', fontSize: '12px' }}>
              Select a tender record from the table to simulate carrier responses.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
