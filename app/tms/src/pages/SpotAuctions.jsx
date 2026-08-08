import React, { useState, useEffect } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import {
  Gavel,
  Clock,
  TrendingDown,
  CheckCircle2,
  AlertOctagon,
  Plus,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';

export default function SpotAuctions() {
  const { state, dispatch, showToast } = useTMS();
  const [selectedAuctionId, setSelectedAuctionId] = useState(state.auctions[0]?.id || 'AUC-501');
  const [isSubmitBidOpen, setIsSubmitBidOpen] = useState(false);

  const [bidForm, setBidForm] = useState({
    carrierName: 'GATI KWE Express',
    bidAmountSAR: 11500,
  });

  const selectedAuction =
    state.auctions.find((a) => a.id === selectedAuctionId) || state.auctions[0];

  // 90s Countdown timer simulation
  const [timerSecs, setTimerSecs] = useState(selectedAuction?.timeRemainingSecs || 90);

  useEffect(() => {
    if (selectedAuction && selectedAuction.status === 'Bidding') {
      const interval = setInterval(() => {
        setTimerSecs((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [selectedAuction]);

  const handleSelectAuction = (id) => {
    setSelectedAuctionId(id);
    const auc = state.auctions.find((a) => a.id === id);
    if (auc) setTimerSecs(auc.timeRemainingSecs || 90);
  };

  const handleSubmitBid = (e) => {
    e.preventDefault();
    if (!selectedAuction) return;

    if (
      selectedAuction.currentLowestBidSAR &&
      bidForm.bidAmountSAR >= selectedAuction.currentLowestBidSAR
    ) {
      showToast(`Bid rejected: Bid must be lower than current lowest bid of SAR ${selectedAuction.currentLowestBidSAR}`, 'error');
      return;
    }

    const newBid = {
      id: `BID-${Math.floor(800 + Math.random() * 200)}`,
      auctionId: selectedAuction.id,
      carrierName: bidForm.carrierName,
      bidAmountSAR: Number(bidForm.bidAmountSAR),
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      isLowest: true,
    };

    dispatch({
      type: 'SUBMIT_SPOT_BID',
      payload: {
        auctionId: selectedAuction.id,
        bid: newBid,
      },
    });

    setIsSubmitBidOpen(false);
    showToast(`New lowest bid SAR ${bidForm.bidAmountSAR} submitted by ${bidForm.carrierName}!`, 'success');
  };

  const handleAwardAuction = (auction) => {
    if (!auction.currentLowestCarrierName) {
      showToast('Cannot award auction without active bids', 'warning');
      return;
    }

    dispatch({
      type: 'AWARD_SPOT_AUCTION',
      payload: {
        auctionId: auction.id,
        shipmentId: auction.shipmentId,
        winningCarrierName: auction.currentLowestCarrierName,
        winningAmountSAR: auction.currentLowestBidSAR,
      },
    });

    showToast(
      `Spot Auction ${auction.id} Awarded to ${auction.currentLowestCarrierName} at SAR ${auction.currentLowestBidSAR}`,
      'success'
    );
  };

  const handleEscalateHumanDispatch = (auction) => {
    showToast(`Auction ${auction.id} escalated to Human Control Tower Dispatcher`, 'warning');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Gavel color="#8b5cf6" size={22} />
            Reverse Spot Auction Market
          </h2>
          <p className="card-subtitle">
            Real-time reverse bidding room when contract waterfall is exhausted or uncontracted lanes arise.
          </p>
        </div>

        <button className="tms-button tms-btn-primary" onClick={() => setIsSubmitBidOpen(true)}>
          <Plus size={16} /> Submit Carrier Bid
        </button>
      </div>

      {/* Main Grid: Left Auctions List, Right Live Auction Room */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '20px' }}>
        {/* Auctions List */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card-header-flex">
            <span className="card-title">Spot Auctions ({state.auctions.length})</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {state.auctions.map((auc) => {
              const isSelected = selectedAuction?.id === auc.id;
              return (
                <div
                  key={auc.id}
                  onClick={() => handleSelectAuction(auc.id)}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: `2px solid ${isSelected ? '#8b5cf6' : 'var(--border-color)'}`,
                    backgroundColor: isSelected ? 'rgba(139, 92, 246, 0.05)' : 'var(--card-bg)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: '700', fontSize: '13px', color: 'var(--dark-text)' }}>
                      {auc.id} ({auc.shipmentId})
                    </span>
                    <StatusBadge status={auc.status} />
                  </div>

                  <div style={{ fontSize: '12px', marginTop: '4px', color: 'var(--secondary-text)' }}>
                    Route: {auc.origin} ➔ {auc.destinationZone}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px' }}>
                    <span>Reserve: SAR {auc.reservePriceSAR?.toLocaleString()}</span>
                    <span style={{ fontWeight: '700', color: '#16a34a' }}>
                      Lowest: SAR {auc.currentLowestBidSAR?.toLocaleString() || 'None'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Panel: Live Auction Room Details & Bids Stream */}
        {selectedAuction ? (
          <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="card-subtitle">Active Reverse Auction Room</span>
                <div style={{ fontSize: '18px', fontWeight: '800', color: 'var(--dark-text)', marginTop: '2px' }}>
                  {selectedAuction.id} for Shipment {selectedAuction.shipmentId}
                </div>
              </div>
              <StatusBadge status={selectedAuction.status} />
            </div>

            {/* Auction Timer & Lowest Price Banner */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ padding: '16px', background: 'rgba(139, 92, 246, 0.08)', borderRadius: '10px', border: '1px solid #8b5cf6' }}>
                <div className="card-subtitle" style={{ color: '#7c3aed' }}>Current Lowest Spot Bid</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#16a34a', marginTop: '2px' }}>
                  SAR {selectedAuction.currentLowestBidSAR?.toLocaleString() || 'No Bids'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>
                  By: {selectedAuction.currentLowestCarrierName || 'N/A'}
                </div>
              </div>

              <div style={{ padding: '16px', background: 'rgba(245, 158, 11, 0.08)', borderRadius: '10px', border: '1px solid #f59e0b' }}>
                <div className="card-subtitle" style={{ color: '#d97706' }}>Auction Countdown Timer</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#d97706', fontFamily: 'monospace', marginTop: '2px' }}>
                  00:{timerSecs < 10 ? `0${timerSecs}` : timerSecs}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>
                  Reserve Cap: SAR {selectedAuction.reservePriceSAR?.toLocaleString()}
                </div>
              </div>
            </div>

            {/* Bids Stream Table */}
            <div>
              <div className="card-subtitle" style={{ marginBottom: '8px' }}>Submitted Carrier Bids ({selectedAuction.bids?.length || 0})</div>
              <div className="tms-table-container">
                <table className="tms-table">
                  <thead>
                    <tr>
                      <th>Carrier Name</th>
                      <th>Bid Amount (SAR)</th>
                      <th>Timestamp</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedAuction.bids?.map((b) => (
                      <tr key={b.id}>
                        <td style={{ fontWeight: '600' }}>{b.carrierName}</td>
                        <td style={{ fontWeight: '700', color: b.isLowest ? '#16a34a' : 'var(--dark-text)' }}>
                          SAR {b.bidAmountSAR.toLocaleString()}
                        </td>
                        <td style={{ fontSize: '11px' }}>{b.timestamp.split(' ')[1]}</td>
                        <td>
                          {b.isLowest ? (
                            <span style={{ fontSize: '11px', fontWeight: '700', color: '#16a34a' }}>Lowest Lead</span>
                          ) : (
                            <span style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>Outbid</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Action Buttons */}
            {selectedAuction.status === 'Bidding' && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button
                  className="tms-button tms-btn-primary"
                  style={{ flex: 1, height: '40px' }}
                  onClick={() => handleAwardAuction(selectedAuction)}
                >
                  <CheckCircle2 size={16} /> Award Auction to Lowest Bidder
                </button>

                <button
                  className="tms-button tms-btn-secondary"
                  style={{ height: '40px' }}
                  onClick={() => handleEscalateHumanDispatch(selectedAuction)}
                >
                  <AlertOctagon size={16} color="#ef4444" /> Escalate to Human Dispatch
                </button>
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--secondary-text)', fontSize: '12px' }}>
            Select a spot auction from the list.
          </div>
        )}
      </div>

      {/* Submit Bid Modal */}
      {isSubmitBidOpen && (
        <Modal title="Submit Carrier Reverse Spot Bid" isOpen={isSubmitBidOpen} onClose={() => setIsSubmitBidOpen(false)}>
          <form onSubmit={handleSubmitBid} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label className="card-subtitle">Select Carrier Partner</label>
              <select
                className="tms-select"
                style={{ width: '100%', marginTop: '4px' }}
                value={bidForm.carrierName}
                onChange={(e) => setBidForm({ ...bidForm, carrierName: e.target.value })}
              >
                {state.carriers.map((c) => (
                  <option key={c.id} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="card-subtitle">Spot Bid Linehaul Amount (SAR)</label>
              <input
                type="number"
                className="tms-input"
                style={{ width: '100%', marginTop: '4px' }}
                value={bidForm.bidAmountSAR}
                onChange={(e) => setBidForm({ ...bidForm, bidAmountSAR: Number(e.target.value) })}
                required
              />
              <span style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '4px', display: 'block' }}>
                Must be lower than current lowest bid of SAR {selectedAuction?.currentLowestBidSAR || selectedAuction?.reservePriceSAR}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button type="button" className="tms-button tms-btn-secondary" onClick={() => setIsSubmitBidOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="tms-button tms-btn-primary">
                Submit Bid
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
