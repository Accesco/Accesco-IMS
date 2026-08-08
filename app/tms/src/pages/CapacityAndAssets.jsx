import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import Pagination from '../components/Pagination';
import {
  Truck,
  Plus,
  Search,
  Wrench,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  Edit,
  XCircle
} from 'lucide-react';

export default function CapacityAndAssets() {
  const { state, dispatch, showToast } = useTMS();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const [newAsset, setNewAsset] = useState({
    vehicleReg: 'KA-04-AB-1234',
    vehicleType: 'Heavy Truck (18T)',
    transportMode: 'FTL',
    maxWeightKg: 18000,
    maxVolumeCbm: 60.0,
    reeferCapable: false,
    tempRange: 'N/A',
    currentLocation: 'Bengaluru Central Hub',
    status: 'Available',
    carrierName: 'Accesco Express Logistics',
  });

  const filteredAssets = state.assets.filter((a) => {
    const matchesSearch =
      a.id.toLowerCase().includes(search.toLowerCase()) ||
      a.vehicleReg.toLowerCase().includes(search.toLowerCase()) ||
      a.carrierName?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'All' || a.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleCreateAsset = (e) => {
    e.preventDefault();
    const assetId = `AST-V${Math.floor(10 + Math.random() * 90)}`;
    const created = {
      ...newAsset,
      id: assetId,
      currentWeightKg: 0,
      currentVolumeCbm: 0,
      weightUtilPct: 0,
      volumeUtilPct: 0,
      assignedShipmentId: null,
      lastInspection: '2026-07-28',
      nextMaintenance: '2026-08-28',
    };

    dispatch({ type: 'ADD_ASSET', payload: created });
    setIsAddModalOpen(false);
    showToast(`Registered new asset ${created.vehicleReg} (${created.id})`, 'success');
  };

  const handleToggleMaintenance = (asset) => {
    const newStatus = asset.status === 'Maintenance' ? 'Available' : 'Maintenance';
    dispatch({
      type: 'UPDATE_ASSET',
      payload: { id: asset.id, status: newStatus },
    });
    showToast(`Updated ${asset.id} status to ${newStatus}`, 'info');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Truck color="var(--primary-blue)" size={22} />
            Capacity & Fleet Asset Management
          </h2>
          <p className="card-subtitle">
            Monitors real-time weight/cubic payload volume density, maintenance status, and vehicle assignments.
          </p>
        </div>

        <button className="tms-button tms-btn-primary" onClick={() => setIsAddModalOpen(true)}>
          <Plus size={16} /> Add Fleet Asset
        </button>
      </div>

      {/* Toolbar */}
      <div className="tms-card" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--secondary-text)' }} />
          <input
            type="text"
            className="tms-input"
            style={{ width: '100%', paddingLeft: '36px' }}
            placeholder="Search asset ID, vehicle reg, carrier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select className="tms-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="All">All Operating Statuses</option>
          <option value="Available">Available</option>
          <option value="Reserved">Reserved</option>
          <option value="In Transit">In Transit</option>
          <option value="Maintenance">Maintenance</option>
        </select>
      </div>

      {/* Assets Grid */}
      <div className="grid-3">
        {filteredAssets.map((asset) => (
          <div key={asset.id} className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--dark-text)' }}>
                  {asset.vehicleReg}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>
                  {asset.id} · {asset.vehicleType}
                </div>
              </div>
              <StatusBadge status={asset.status} />
            </div>

            <div style={{ fontSize: '12px', color: 'var(--dark-text)' }}>
              <div><strong>Carrier:</strong> {asset.carrierName}</div>
              <div><strong>Location:</strong> {asset.currentLocation}</div>
              {asset.assignedShipmentId && (
                <div><strong>Assigned Shipment:</strong> <span style={{ color: 'var(--primary-blue)', fontWeight: '700' }}>{asset.assignedShipmentId}</span></div>
              )}
            </div>

            {/* Utilisation Progress Bars */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '10px', background: 'var(--bg-color)', borderRadius: '8px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: '600' }}>
                  <span>Weight Payload</span>
                  <span>{asset.currentWeightKg.toLocaleString()} / {asset.maxWeightKg.toLocaleString()} kg ({asset.weightUtilPct}%)</span>
                </div>
                <div style={{ height: '6px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden', marginTop: '2px' }}>
                  <div style={{ width: `${Math.min(100, asset.weightUtilPct)}%`, height: '100%', background: asset.weightUtilPct > 90 ? '#ef4444' : '#2563eb' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: '600' }}>
                  <span>Volumetric Cube</span>
                  <span>{asset.currentVolumeCbm} / {asset.maxVolumeCbm} CBM ({asset.volumeUtilPct}%)</span>
                </div>
                <div style={{ height: '6px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden', marginTop: '2px' }}>
                  <div style={{ width: `${Math.min(100, asset.volumeUtilPct)}%`, height: '100%', background: asset.volumeUtilPct > 90 ? '#ef4444' : '#06b6d4' }} />
                </div>
              </div>
            </div>

            {asset.weightUtilPct > 90 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#d97706', fontWeight: '600' }}>
                <AlertTriangle size={14} /> Capacity utilisation exceeds 90% threshold
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginTop: '4px' }}>
              <button
                className={`tms-button tms-btn-sm ${asset.status === 'Maintenance' ? 'tms-btn-primary' : 'tms-btn-secondary'}`}
                onClick={() => handleToggleMaintenance(asset)}
              >
                <Wrench size={12} /> {asset.status === 'Maintenance' ? 'Set Available' : 'Maintenance'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Asset Modal */}
      {isAddModalOpen && (
        <Modal title="Register Fleet Asset" isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)}>
          <form onSubmit={handleCreateAsset} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label className="card-subtitle">Vehicle Registration</label>
              <input
                type="text"
                className="tms-input"
                style={{ width: '100%', marginTop: '4px' }}
                value={newAsset.vehicleReg}
                onChange={(e) => setNewAsset({ ...newAsset, vehicleReg: e.target.value })}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label className="card-subtitle">Vehicle Type</label>
                <select
                  className="tms-select"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newAsset.vehicleType}
                  onChange={(e) => setNewAsset({ ...newAsset, vehicleType: e.target.value })}
                >
                  <option value="Light Commercial Vehicle">Light Commercial Vehicle (LCV)</option>
                  <option value="Medium Truck (10T)">Medium Truck (10T)</option>
                  <option value="Heavy Truck (18T)">Heavy Truck (18T)</option>
                  <option value="Reefer Truck (18T)">Reefer Truck (18T)</option>
                  <option value="Container Vehicle (18T)">Container Vehicle (18T)</option>
                </select>
              </div>

              <div>
                <label className="card-subtitle">Carrier Partner</label>
                <select
                  className="tms-select"
                  style={{ width: '100%', marginTop: '4px' }}
                  value={newAsset.carrierName}
                  onChange={(e) => setNewAsset({ ...newAsset, carrierName: e.target.value })}
                >
                  {state.carriers.map((c) => (
                    <option key={c.id} value={c.name}>{c.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button type="button" className="tms-button tms-btn-secondary" onClick={() => setIsAddModalOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="tms-button tms-btn-primary">
                Register Asset
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
