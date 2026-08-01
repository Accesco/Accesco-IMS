import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import {
  Server,
  Activity,
  Radio,
  CheckCircle2,
  XCircle,
  RotateCw,
  Search,
  Filter,
  Zap
} from 'lucide-react';

export default function IntegrationMonitor() {
  const { state, dispatch, showToast } = useTMS();
  const [search, setSearch] = useState('');

  const services = [
    {
      name: 'Accesco ERP Rest Gateway',
      channel: 'ERP-REST-v2',
      status: 'Connected',
      latencyMs: 14,
      throughputRps: '140 req/s',
      lastHeartbeat: '2 secs ago',
    },
    {
      name: 'order-events Ingestion Stream',
      channel: 'order-events',
      status: 'Active',
      latencyMs: 8,
      throughputRps: '85 msg/s',
      lastHeartbeat: '1 sec ago',
    },
    {
      name: 'procurement-tenders Stream',
      channel: 'procurement-tenders',
      status: 'Active',
      latencyMs: 12,
      throughputRps: '42 msg/s',
      lastHeartbeat: '3 secs ago',
    },
    {
      name: 'IoT Telematics Sensor Feed',
      channel: 'iot-telemetry',
      status: 'Active',
      latencyMs: 6,
      throughputRps: '320 msg/s',
      lastHeartbeat: '1 sec ago',
    },
  ];

  const handleSimulateStreamFailure = () => {
    showToast('Simulated temporary network partition on order-events stream. Auto-reconnecting...', 'warning');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server color="var(--primary-blue)" size={22} />
            Integration Bus & Stream Monitor
          </h2>
          <p className="card-subtitle">
            Monitors real-time API connection gateways, Kafka order event streams, and telematics message feeds.
          </p>
        </div>

        <button className="tms-button tms-btn-secondary" onClick={handleSimulateStreamFailure}>
          <Zap size={16} color="#f59e0b" /> Simulate Stream Interruption
        </button>
      </div>

      {/* Connection Status Cards */}
      <div className="grid-4">
        {services.map((srv, idx) => (
          <div key={idx} className="tms-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--dark-text)' }}>{srv.name}</div>
                <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>{srv.channel}</div>
              </div>
              <StatusBadge status={srv.status} />
            </div>

            <div style={{ fontSize: '11px', color: 'var(--dark-text)', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Latency:</span> <strong style={{ color: '#16a34a' }}>{srv.latencyMs} ms</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Throughput:</span> <strong>{srv.throughputRps}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Heartbeat:</span> <span style={{ color: 'var(--secondary-text)' }}>{srv.lastHeartbeat}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Integration Events Stream Log Table */}
      <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="card-header-flex">
          <span className="card-title">Event Bus Stream Feed Log</span>
        </div>

        <div className="tms-table-container">
          <table className="tms-table">
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Channel</th>
                <th>Source</th>
                <th>Payload Summary</th>
                <th>Timestamp</th>
                <th>Processing Status</th>
              </tr>
            </thead>
            <tbody>
              {state.orders.slice(0, 8).map((o, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)', fontFamily: 'monospace' }}>
                    EVT-{78300 + idx}
                  </td>
                  <td>order-events</td>
                  <td>Accesco-ERP-Gateway</td>
                  <td style={{ fontSize: '12px' }}>
                    Order Intake {o.erpRef} ({o.weightKg} kg, {o.destinationZone})
                  </td>
                  <td style={{ fontSize: '11px' }}>{o.integrationTimestamp}</td>
                  <td>
                    <StatusBadge status="Processed" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
