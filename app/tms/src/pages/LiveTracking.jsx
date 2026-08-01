import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import SimulatedMapCanvas from '../components/SimulatedMapCanvas';
import StatusBadge from '../components/StatusBadge';
import {
  Navigation,
  Thermometer,
  Gauge,
  Clock,
  AlertTriangle,
  Play,
  RotateCw,
  Radio,
  CheckCircle2
} from 'lucide-react';

export default function LiveTracking() {
  const { state, dispatch, showToast } = useTMS();
  const [selectedShipmentId, setSelectedShipmentId] = useState(
    state.shipments.find((s) => s.shipmentStatus === 'In Transit')?.id || 'SHP-8802'
  );

  const selectedShipment =
    state.shipments.find((s) => s.id === selectedShipmentId) || state.shipments[0];

  const shipmentTelemetry = (state.telemetryEvents || state.telemetry || []).filter(
    (t) => t.shipmentId === selectedShipmentId
  );

  // Simulation Controls Handlers
  const handleSimulateNormalPing = () => {
    const event = {
      id: `TLM-${Date.now()}`,
      shipmentId: selectedShipmentId,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      lat: (selectedShipment.currentLat || 15.36) + (Math.random() - 0.5) * 0.05,
      lng: (selectedShipment.currentLng || 75.12) + (Math.random() - 0.5) * 0.05,
      speedKmh: 68,
      reeferTempC: selectedShipment.isReefer ? 4.2 : null,
      eta: 'On Schedule (18:45)',
      etaDriftMins: 0,
      geofenceStatus: 'Inside Transit Corridor',
      eventSource: 'GPS Gateway Feed',
      processingStatus: 'Processed',
    };

    dispatch({
      type: 'ADD_TELEMETRY_EVENT',
      payload: {
        telemetry: event,
        updatedShipment: {
          id: selectedShipmentId,
          currentLat: event.lat,
          currentLng: event.lng,
          speedKmh: event.speedKmh,
        },
      },
    });

    showToast(`Injected GPS Ping for ${selectedShipmentId}: Speed 68 KM/H, On Schedule`, 'success');
  };

  const handleSimulateTempSpike = () => {
    const event = {
      id: `TLM-${Date.now()}`,
      shipmentId: selectedShipmentId,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      lat: selectedShipment.currentLat || 15.36,
      lng: selectedShipment.currentLng || 75.12,
      speedKmh: 62,
      reeferTempC: 11.5, // Spike above 8°C threshold!
      eta: 'On Schedule (18:45)',
      etaDriftMins: 0,
      geofenceStatus: 'Inside Transit Corridor',
      eventSource: 'IoT Reefer Sensor',
      processingStatus: 'Processed',
    };

    const alert = {
      id: `ALT-${Date.now()}`,
      shipmentId: selectedShipmentId,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      severity: 'Critical',
      type: 'Cold Chain Excursion',
      message: `Reefer temperature spiked to 11.5°C on shipment ${selectedShipmentId} (Max threshold: 8.0°C)`,
      source: 'IoT Sensor Stream',
      isRead: false,
    };

    dispatch({
      type: 'ADD_TELEMETRY_EVENT',
      payload: {
        telemetry: event,
        newAlert: alert,
        updatedShipment: {
          id: selectedShipmentId,
          reeferTempC: 11.5,
        },
      },
    });

    showToast(`CRITICAL ALERT: Reefer Temp Spike (11.5°C) on ${selectedShipmentId}`, 'error');
  };

  const handleSimulateETADrift = () => {
    const event = {
      id: `TLM-${Date.now()}`,
      shipmentId: selectedShipmentId,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      lat: selectedShipment.currentLat || 15.36,
      lng: selectedShipment.currentLng || 75.12,
      speedKmh: 22,
      reeferTempC: selectedShipment.isReefer ? 4.5 : null,
      eta: 'Delayed (19:30)',
      etaDriftMins: 45, // 45 min drift!
      geofenceStatus: 'Traffic Delay Corridor',
      eventSource: 'Telematics Predictor',
      processingStatus: 'Processed',
    };

    const alert = {
      id: `ALT-${Date.now()}`,
      shipmentId: selectedShipmentId,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      severity: 'High',
      type: 'ETA Breach Drift',
      message: `ETA drifted by +45 mins on ${selectedShipmentId}. Revised ETA: 19:30`,
      source: 'Telematics Stream',
      isRead: false,
    };

    dispatch({
      type: 'ADD_TELEMETRY_EVENT',
      payload: {
        telemetry: event,
        newAlert: alert,
        updatedShipment: {
          id: selectedShipmentId,
          etaDriftMins: 45,
          eta: 'Delayed (19:30)',
        },
      },
    });

    showToast(`WARNING: +45 Min ETA Drift simulated on ${selectedShipmentId}`, 'warning');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Navigation color="var(--primary-blue)" size={22} />
            IoT Telematics & Live GPS Tracking
          </h2>
          <p className="card-subtitle">
            Real-time GPS coordinates, vehicle speed, reefer temperature sensors & automated ETA drift prediction.
          </p>
        </div>

        {/* Shipment Selector */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="card-subtitle">Tracking Target:</span>
          <select
            className="tms-select"
            value={selectedShipmentId}
            onChange={(e) => setSelectedShipmentId(e.target.value)}
          >
            {state.shipments.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id} ({s.carrierName || 'Unassigned'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Left Gauges & Controls, Right Map & Telemetry Stream */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        {/* Left Panel: Telemetry Gauges & Simulation Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Active Gauges */}
          <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="card-header-flex">
              <span className="card-title">Live Sensor Telemetry</span>
              <span style={{ fontSize: '11px', color: '#16a34a', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Radio size={12} className="animate-pulse" /> Live Stream
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div style={{ padding: '12px', background: 'var(--bg-color)', borderRadius: '8px', textAlign: 'center' }}>
                <Gauge size={18} color="#2563eb" style={{ margin: '0 auto 4px' }} />
                <div className="card-subtitle">Current Speed</div>
                <div style={{ fontSize: '18px', fontWeight: '800', marginTop: '2px' }}>
                  {selectedShipment?.speedKmh || 64} <span style={{ fontSize: '11px' }}>KM/H</span>
                </div>
              </div>

              <div style={{ padding: '12px', background: 'var(--bg-color)', borderRadius: '8px', textAlign: 'center' }}>
                <Thermometer size={18} color={selectedShipment?.reeferTempC > 8 ? '#ef4444' : '#06b6d4'} style={{ margin: '0 auto 4px' }} />
                <div className="card-subtitle">Reefer Temp</div>
                <div style={{ fontSize: '18px', fontWeight: '800', color: selectedShipment?.reeferTempC > 8 ? '#ef4444' : 'var(--dark-text)', marginTop: '2px' }}>
                  {selectedShipment?.reeferTempC ? `${selectedShipment.reeferTempC}°C` : 'Ambient'}
                </div>
              </div>
            </div>

            <div style={{ padding: '10px', background: 'var(--bg-color)', borderRadius: '8px' }}>
              <div className="card-subtitle">Geofence Status</div>
              <div style={{ fontWeight: '700', fontSize: '12px', marginTop: '2px', color: '#16a34a' }}>
                Inside Approved Highway Transit Corridor
              </div>
            </div>
          </div>

          {/* Telemetry Event Injection Controller */}
          <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="card-header-flex">
              <span className="card-title">Telemetry Injection Controls</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button className="tms-button tms-btn-secondary" onClick={handleSimulateNormalPing}>
                <Play size={14} color="#16a34a" /> Simulate Normal GPS Ping
              </button>

              <button className="tms-button tms-btn-secondary" onClick={handleSimulateTempSpike}>
                <AlertTriangle size={14} color="#ef4444" /> Simulate Reefer Temp Spike (&gt;8°C)
              </button>

              <button className="tms-button tms-btn-secondary" onClick={handleSimulateETADrift}>
                <Clock size={14} color="#f59e0b" /> Simulate +45 Min Traffic ETA Drift
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel: Map Canvas & Telemetry Stream Log Table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="tms-card" style={{ padding: '16px' }}>
            <SimulatedMapCanvas
              origin={selectedShipment?.origin || 'Bengaluru Central Hub'}
              destination={selectedShipment?.destinationName || 'Pune Fulfilment Center'}
              currentLat={selectedShipment?.currentLat || 15.3647}
              currentLng={selectedShipment?.currentLng || 75.1240}
              speedKmh={selectedShipment?.speedKmh || 64}
              exception={selectedShipment?.reeferTempC > 8 ? 'Reefer Excursion' : null}
              height="280px"
            />
          </div>

          {/* Telemetry Events Stream Log Table */}
          <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="card-header-flex">
              <span className="card-title">IoT Telemetry Event Stream Log ({shipmentTelemetry.length})</span>
            </div>

            <div className="tms-table-container">
              <table className="tms-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Source</th>
                    <th>Lat / Lng</th>
                    <th>Speed</th>
                    <th>Temp</th>
                    <th>ETA Status</th>
                    <th>Geofence</th>
                  </tr>
                </thead>
                <tbody>
                  {shipmentTelemetry.map((t) => (
                    <tr key={t.id}>
                      <td style={{ fontSize: '11px', fontWeight: '600' }}>{t.timestamp.split(' ')[1]}</td>
                      <td style={{ fontSize: '11px' }}>{t.eventSource}</td>
                      <td style={{ fontSize: '11px', fontFamily: 'monospace' }}>
                        {t.lat.toFixed(4)}, {t.lng.toFixed(4)}
                      </td>
                      <td style={{ fontWeight: '600' }}>{t.speedKmh} km/h</td>
                      <td style={{ fontWeight: '700', color: t.reeferTempC > 8 ? '#ef4444' : 'var(--dark-text)' }}>
                        {t.reeferTempC ? `${t.reeferTempC}°C` : 'N/A'}
                      </td>
                      <td style={{ fontSize: '11px' }}>{t.eta}</td>
                      <td style={{ fontSize: '11px' }}>{t.geofenceStatus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
