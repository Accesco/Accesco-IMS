import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import SimulatedMapCanvas from '../components/SimulatedMapCanvas';
import StatusBadge from '../components/StatusBadge';
import {
  Route,
  MapPin,
  Sparkles,
  ArrowDownUp,
  Clock,
  CheckCircle2,
  Navigation,
  RotateCw,
  Plus,
  Trash2
} from 'lucide-react';

export default function RoutePlanning() {
  const { state, dispatch, showToast } = useTMS();
  const [selectedShipmentId, setSelectedShipmentId] = useState(state.shipments[0]?.id || 'SHP-8801');

  const selectedShipment =
    state.shipments.find((s) => s.id === selectedShipmentId) || state.shipments[0];

  const [stops, setStops] = useState(selectedShipment?.stops || []);

  const handleSelectShipment = (id) => {
    setSelectedShipmentId(id);
    const shp = state.shipments.find((s) => s.id === id);
    if (shp) setStops(shp.stops || []);
  };

  const handleOptimizeSequence = () => {
    // Reorder stops by delivery window deadline
    const sorted = [...stops].sort(
      (a, b) => new Date(a.deadline || 0) - new Date(b.deadline || 0)
    );
    setStops(sorted);
    showToast(`Optimised stop sequence for ${selectedShipment?.id} based on window deadlines`, 'success');
  };

  const handleRecalculateETA = () => {
    showToast(`Recalculated ETA for ${selectedShipment?.id}: 2026-07-30T11:15 (On Schedule)`, 'info');
  };

  const handleApproveRoute = () => {
    showToast(`Approved & Saved Route Plan for ${selectedShipment?.id}`, 'success');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Route color="var(--primary-blue)" size={22} />
            Route Planning & Sequential Mapping
          </h2>
          <p className="card-subtitle">
            Geographic spatial grouping, delivery window deadlines, and multi-stop route optimisation.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="tms-button tms-btn-secondary" onClick={handleOptimizeSequence}>
            <Sparkles size={14} color="#2563eb" /> Optimise Sequence
          </button>
          <button className="tms-button tms-btn-primary" onClick={handleApproveRoute}>
            <CheckCircle2 size={14} /> Approve Route Plan
          </button>
        </div>
      </div>

      {/* Main Grid: Left Selector & Stops, Right Map Canvas */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        {/* Left Panel: Shipment Selector & Stops Editor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="tms-card" style={{ padding: '16px' }}>
            <label className="card-subtitle" style={{ display: 'block', marginBottom: '6px' }}>Select Active Freight Shipment</label>
            <select
              className="tms-select"
              style={{ width: '100%' }}
              value={selectedShipmentId}
              onChange={(e) => handleSelectShipment(e.target.value)}
            >
              {state.shipments.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id} ({s.origin} ➔ {s.destinationZone})
                </option>
              ))}
            </select>
          </div>

          {/* Stops List */}
          <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="card-header-flex">
              <span className="card-title">Sequential Stops ({stops.length})</span>
              <button className="tms-button tms-btn-secondary tms-btn-sm" onClick={handleRecalculateETA}>
                <RotateCw size={12} /> Recalculate
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {stops.map((st, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div
                      style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        background: idx === 0 ? '#1e40af' : idx === stops.length - 1 ? '#16a34a' : '#374151',
                        color: '#ffffff',
                        fontSize: '11px',
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {idx + 1}
                    </div>
                    <div>
                      <div style={{ fontWeight: '700', fontSize: '13px' }}>{st.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>
                        Type: {st.type} | Deadline: {st.deadline ? st.deadline.replace('T', ' ') : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel: Simulated Map Diagram */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header-flex">
            <span className="card-title">Live Visual Route Diagram</span>
            <span className="card-subtitle">GPS Coordinates & Waypoint Vector</span>
          </div>

          <SimulatedMapCanvas
            origin={selectedShipment?.origin || 'Bengaluru Central Hub'}
            destination={selectedShipment?.destinationName || 'Pune Fulfilment Center'}
            currentLat={selectedShipment?.currentLat || 15.3647}
            currentLng={selectedShipment?.currentLng || 75.1240}
            speedKmh={selectedShipment?.speedKmh || 64}
            stops={stops}
            height="380px"
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginTop: '8px' }}>
            <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '8px', textAlign: 'center' }}>
              <div className="card-subtitle">Planned Distance</div>
              <div style={{ fontWeight: '700', fontSize: '14px', marginTop: '2px' }}>840 KM</div>
            </div>
            <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '8px', textAlign: 'center' }}>
              <div className="card-subtitle">Est. Duration</div>
              <div style={{ fontWeight: '700', fontSize: '14px', marginTop: '2px' }}>14 hrs 30 mins</div>
            </div>
            <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '8px', textAlign: 'center' }}>
              <div className="card-subtitle">Current ETA</div>
              <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--primary-blue)', marginTop: '2px' }}>
                {selectedShipment?.eta || 'On Schedule'}
              </div>
            </div>
            <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '8px', textAlign: 'center' }}>
              <div className="card-subtitle">ETA Drift</div>
              <div style={{ fontWeight: '700', fontSize: '14px', color: '#16a34a', marginTop: '2px' }}>+15 mins</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
