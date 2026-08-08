import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import {
  Handshake,
  Plus,
  Search,
  Award,
  AlertTriangle,
  FileCheck,
  Building2,
  FileText
} from 'lucide-react';

export default function CarrierManagement() {
  const { state, dispatch, showToast } = useTMS();
  const [activeTab, setActiveTab] = useState('carriers'); // 'carriers' or 'tariffs'
  const [search, setSearch] = useState('');
  const [isAddCarrierOpen, setIsAddCarrierOpen] = useState(false);
  const [isAddTariffOpen, setIsAddTariffOpen] = useState(false);

  const [newCarrier, setNewCarrier] = useState({
    name: 'TCI Express Surface',
    scac: 'TCIE',
    supportedZones: ['South Zone', 'West Zone'],
    supportedModes: ['FTL', 'LTL'],
    contactName: 'Ramesh Patel',
    contactEmail: 'ramesh@tciexpress.in',
    contactPhone: '+91 98990 12345',
  });

  const [newTariff, setNewTariff] = useState({
    carrierName: 'Accesco Express Logistics',
    originZone: 'South Zone',
    destinationZone: 'West Zone',
    transportMode: 'FTL',
    baseLinehaulSAR: 4500,
    fuelSurchargePct: 12.0,
    accessorialBufferSAR: 300,
  });

  const filteredCarriers = state.carriers.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.scac.toLowerCase().includes(search.toLowerCase())
  );

  const filteredTariffs = state.tariffs.filter(
    (t) =>
      t.carrierName.toLowerCase().includes(search.toLowerCase()) ||
      t.originZone.toLowerCase().includes(search.toLowerCase()) ||
      t.destinationZone.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreateCarrier = (e) => {
    e.preventDefault();
    const carrierId = `CRR-${Math.floor(100 + Math.random() * 900)}`;
    const created = {
      ...newCarrier,
      id: carrierId,
      status: 'Active',
      maxWeightCapacityKg: 200000,
      maxVolumeCbm: 700,
      reeferCapability: false,
      onTimeCompliancePct: 95.0,
      tenderAcceptanceRatePct: 90.0,
      performanceTier: 'Tier 2 (Gold)',
      tierScorePct: 90.0,
      slaBreaches: 0,
      activeContracts: 2,
      activeShipments: 0,
    };

    dispatch({ type: 'ADD_CARRIER', payload: created });
    setIsAddCarrierOpen(false);
    showToast(`Registered new Carrier ${created.name} (${created.scac})`, 'success');
  };

  const handleCreateTariff = (e) => {
    e.preventDefault();
    const tariffId = `TRF-${Math.floor(200 + Math.random() * 800)}`;
    const created = {
      ...newTariff,
      id: tariffId,
      effectiveDate: '2026-01-01',
      expiryDate: '2026-12-31',
      validationStatus: 'Active',
      maxWeightKg: 18000,
      maxVolumeCbm: 60.0,
      slaResponseTimeMins: 60,
    };

    dispatch({ type: 'ADD_TARIFF', payload: created });
    setIsAddTariffOpen(false);
    showToast(`Added new contracted tariff ${created.id} for ${created.carrierName}`, 'success');
  };

  const handleToggleSuspend = (carrier) => {
    const newStatus = carrier.status === 'Suspended' ? 'Active' : 'Suspended';
    dispatch({
      type: 'UPDATE_CARRIER',
      payload: { id: carrier.id, status: newStatus },
    });
    showToast(`Updated carrier ${carrier.name} status to ${newStatus}`, 'info');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Handshake color="var(--primary-blue)" size={22} />
            Carrier Partner & Tariff Contract Register
          </h2>
          <p className="card-subtitle">
            Carrier ranking leaderboard, contract rate tariffs, SLA breach logs, and 2.5% penalty tier scores.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-color)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <button
              className={`tms-button ${activeTab === 'carriers' ? 'tms-btn-primary' : 'tms-btn-secondary'}`}
              style={{ height: '32px', fontSize: '12px' }}
              onClick={() => setActiveTab('carriers')}
            >
              <Building2 size={14} /> Carriers ({state.carriers.length})
            </button>
            <button
              className={`tms-button ${activeTab === 'tariffs' ? 'tms-btn-primary' : 'tms-btn-secondary'}`}
              style={{ height: '32px', fontSize: '12px' }}
              onClick={() => setActiveTab('tariffs')}
            >
              <FileText size={14} /> Contracted Tariffs ({state.tariffs.length})
            </button>
          </div>

          {activeTab === 'carriers' ? (
            <button className="tms-button tms-btn-primary" onClick={() => setIsAddCarrierOpen(true)}>
              <Plus size={16} /> Add Carrier
            </button>
          ) : (
            <button className="tms-button tms-btn-primary" onClick={() => setIsAddTariffOpen(true)}>
              <Plus size={16} /> Add Tariff Rate
            </button>
          )}
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
            placeholder={activeTab === 'carriers' ? 'Search carrier name, SCAC...' : 'Search carrier or lane...'}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Carriers View */}
      {activeTab === 'carriers' && (
        <div className="tms-table-container">
          <table className="tms-table">
            <thead>
              <tr>
                <th>Carrier Name & SCAC</th>
                <th>Status</th>
                <th>Performance Tier</th>
                <th>Tier Score</th>
                <th>On-Time %</th>
                <th>Tender Acc %</th>
                <th>SLA Breaches</th>
                <th>Active Runs</th>
                <th>Contact Person</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCarriers.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{c.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>{c.id} · SCAC: {c.scac}</div>
                  </td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>
                    <span style={{ fontWeight: '700', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Award size={14} /> {c.performanceTier}
                    </span>
                  </td>
                  <td style={{ fontWeight: '700' }}>{c.tierScorePct}%</td>
                  <td style={{ color: '#16a34a', fontWeight: '600' }}>{c.onTimeCompliancePct}%</td>
                  <td style={{ color: '#2563eb', fontWeight: '600' }}>{c.tenderAcceptanceRatePct}%</td>
                  <td>
                    <span style={{ fontWeight: '700', color: c.slaBreaches > 0 ? '#ef4444' : 'var(--dark-text)' }}>
                      {c.slaBreaches}
                    </span>
                  </td>
                  <td>{c.activeShipments}</td>
                  <td style={{ fontSize: '12px' }}>
                    <div>{c.contactName}</div>
                    <div style={{ color: 'var(--secondary-text)' }}>{c.contactEmail}</div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className={`tms-button tms-btn-sm ${c.status === 'Suspended' ? 'tms-btn-primary' : 'tms-btn-outline-danger'}`}
                      onClick={() => handleToggleSuspend(c)}
                    >
                      {c.status === 'Suspended' ? 'Reactivate' : 'Suspend'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tariffs View */}
      {activeTab === 'tariffs' && (
        <div className="tms-table-container">
          <table className="tms-table">
            <thead>
              <tr>
                <th>Tariff ID</th>
                <th>Carrier Name</th>
                <th>Origin Zone</th>
                <th>Destination Zone</th>
                <th>Mode</th>
                <th>Base Linehaul (SAR)</th>
                <th>Fuel Surcharge</th>
                <th>SLA Timer</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredTariffs.map((t) => (
                <tr key={t.id}>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{t.id}</td>
                  <td style={{ fontWeight: '600' }}>{t.carrierName}</td>
                  <td>{t.originZone}</td>
                  <td>{t.destinationZone}</td>
                  <td>{t.transportMode}</td>
                  <td style={{ fontWeight: '700' }}>SAR {t.baseLinehaulSAR.toLocaleString()}</td>
                  <td>{t.fuelSurchargePct}%</td>
                  <td>{t.slaResponseTimeMins} mins</td>
                  <td>
                    <StatusBadge status={t.validationStatus} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Carrier Modal */}
      {isAddCarrierOpen && (
        <Modal title="Register Carrier Partner" isOpen={isAddCarrierOpen} onClose={() => setIsAddCarrierOpen(false)}>
          <form onSubmit={handleCreateCarrier} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label className="card-subtitle">Carrier Legal Name</label>
              <input
                type="text"
                className="tms-input"
                style={{ width: '100%', marginTop: '4px' }}
                value={newCarrier.name}
                onChange={(e) => setNewCarrier({ ...newCarrier, name: e.target.value })}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label className="card-subtitle">SCAC Code</label>
                <input
                  type="text"
                  className="tms-input"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newCarrier.scac}
                  onChange={(e) => setNewCarrier({ ...newCarrier, scac: e.target.value })}
                  required
                />
              </div>

              <div>
                <label className="card-subtitle">Contact Person Name</label>
                <input
                  type="text"
                  className="tms-input"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newCarrier.contactName}
                  onChange={(e) => setNewCarrier({ ...newCarrier, contactName: e.target.value })}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button type="button" className="tms-button tms-btn-secondary" onClick={() => setIsAddCarrierOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="tms-button tms-btn-primary">
                Register Partner
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Add Tariff Modal */}
      {isAddTariffOpen && (
        <Modal title="Add Contracted Tariff Rate" isOpen={isAddTariffOpen} onClose={() => setIsAddTariffOpen(false)}>
          <form onSubmit={handleCreateTariff} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label className="card-subtitle">Carrier Partner</label>
              <select
                className="tms-select"
                style={{ width: '100%', marginTop: '4px' }}
                value={newTariff.carrierName}
                onChange={(e) => setNewTariff({ ...newTariff, carrierName: e.target.value })}
              >
                {state.carriers.map((c) => (
                  <option key={c.id} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label className="card-subtitle">Origin Zone</label>
                <select
                  className="tms-select"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newTariff.originZone}
                  onChange={(e) => setNewTariff({ ...newTariff, originZone: e.target.value })}
                >
                  <option value="South Zone">South Zone</option>
                  <option value="West Zone">West Zone</option>
                  <option value="North Zone">North Zone</option>
                  <option value="Central Zone">Central Zone</option>
                </select>
              </div>

              <div>
                <label className="card-subtitle">Destination Zone</label>
                <select
                  className="tms-select"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newTariff.destinationZone}
                  onChange={(e) => setNewTariff({ ...newTariff, destinationZone: e.target.value })}
                >
                  <option value="West Zone">West Zone</option>
                  <option value="South Zone">South Zone</option>
                  <option value="North Zone">North Zone</option>
                  <option value="Central Zone">Central Zone</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label className="card-subtitle">Base Linehaul Rate (SAR)</label>
                <input
                  type="number"
                  className="tms-input"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newTariff.baseLinehaulSAR}
                  onChange={(e) => setNewTariff({ ...newTariff, baseLinehaulSAR: Number(e.target.value) })}
                  required
                />
              </div>

              <div>
                <label className="card-subtitle">Fuel Surcharge %</label>
                <input
                  type="number"
                  className="tms-input"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newTariff.fuelSurchargePct}
                  onChange={(e) => setNewTariff({ ...newTariff, fuelSurchargePct: Number(e.target.value) })}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button type="button" className="tms-button tms-btn-secondary" onClick={() => setIsAddTariffOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="tms-button tms-btn-primary">
                Save Tariff Rate
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
