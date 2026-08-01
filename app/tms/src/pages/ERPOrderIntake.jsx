import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import Drawer from '../components/Drawer';
import Pagination from '../components/Pagination';
import ConfirmDialog from '../components/ConfirmDialog';
import {
  FileSpreadsheet,
  Plus,
  Search,
  Filter,
  Eye,
  CheckCircle2,
  RotateCw,
  XCircle,
  ArrowRight,
  Code,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';

export default function ERPOrderIntake() {
  const { state, dispatch, showToast } = useTMS();
  const [search, setSearch] = useState('');
  const [integrationFilter, setIntegrationFilter] = useState('All');
  const [originFilter, setOriginFilter] = useState('All');
  const [zoneFilter, setZoneFilter] = useState('All');
  const [allocationFilter, setAllocationFilter] = useState('All');

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [selectedOrderPayload, setSelectedOrderPayload] = useState(null);
  const [confirmRejectOrder, setConfirmRejectOrder] = useState(null);

  // Filtered orders
  const filteredOrders = state.orders.filter((o) => {
    const matchesSearch =
      o.erpRef.toLowerCase().includes(search.toLowerCase()) ||
      o.id.toLowerCase().includes(search.toLowerCase()) ||
      o.destinationName.toLowerCase().includes(search.toLowerCase());

    const matchesIntegration =
      integrationFilter === 'All' || o.integrationStatus === integrationFilter;
    const matchesOrigin =
      originFilter === 'All' || o.originComplexId === originFilter || o.originName === originFilter;
    const matchesZone =
      zoneFilter === 'All' || o.destinationZone === zoneFilter;
    const matchesAllocation =
      allocationFilter === 'All' || o.allocationStatus === allocationFilter;

    return matchesSearch && matchesIntegration && matchesOrigin && matchesZone && matchesAllocation;
  });

  const totalPages = Math.ceil(filteredOrders.length / pageSize);
  const paginatedOrders = filteredOrders.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Action: Simulate ERP Order Intake
  const handleSimulateERPOrder = () => {
    const randomId = Math.floor(1000 + Math.random() * 9000);
    const hubs = [
      { id: 'BGL-CENTRAL', name: 'Bengaluru Central Hub' },
      { id: 'BGL-NORTH', name: 'Bengaluru North Hub' },
      { id: 'HYD-HUB', name: 'Hyderabad Hub' },
      { id: 'CHN-HUB', name: 'Chennai Hub' },
      { id: 'MUM-HUB', name: 'Mumbai Hub' },
    ];
    const hub = hubs[Math.floor(Math.random() * hubs.length)];

    const zones = ['South Zone', 'West Zone', 'North Zone', 'Central Zone', 'East Zone'];
    const zone = zones[Math.floor(Math.random() * zones.length)];

    const categories = ['Modular Kitchens', 'Upholstered Seating', 'Bedroom Sets', 'Office Systems', 'Dining Collections'];
    const category = categories[Math.floor(Math.random() * categories.length)];

    const newOrder = {
      id: `TMS-ORD-${randomId}`,
      erpRef: `ERP-${78300 + Math.floor(Math.random() * 500)}`,
      originComplexId: hub.id,
      originName: hub.name,
      destinationName: `${zone.split(' ')[0]} Hub Terminal ${randomId % 10}`,
      destinationAddress: `Sector ${randomId % 50}, Express Freight Park, ${zone}`,
      lat: 12.9 + (Math.random() * 10),
      lng: 77.5 + (Math.random() * 10),
      destinationZone: zone,
      weightKg: Math.floor(2000 + Math.random() * 12000),
      volumeCbm: Number((8 + Math.random() * 35).toFixed(1)),
      windowStart: '2026-07-28T09:00',
      windowEnd: '2026-07-30T18:00',
      priority: Math.random() > 0.5 ? 'High' : 'Medium',
      productCategory: category,
      tempRequirement: Math.random() > 0.8 ? 'Reefer (2°C - 8°C)' : 'Ambient',
      integrationTimestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      integrationStatus: 'Validated',
      allocationStatus: 'Unallocated',
    };

    dispatch({ type: 'SIMULATE_ERP_ORDER', payload: newOrder });
    showToast(`ERP Order ${newOrder.erpRef} ingested & validated as ${newOrder.id}`, 'success');
  };

  // Action: Validate Order
  const handleValidateOrder = (order) => {
    // Check validation rules
    if (!order.erpRef || !order.originComplexId || !order.lat || !order.lng || order.weightKg <= 0 || order.volumeCbm <= 0) {
      dispatch({
        type: 'UPDATE_ORDER_STATUS',
        payload: { orderId: order.id, integrationStatus: 'Validation Failed' },
      });
      showToast(`Validation Failed for ${order.erpRef}: Missing or invalid attributes`, 'error');
    } else {
      dispatch({
        type: 'UPDATE_ORDER_STATUS',
        payload: { orderId: order.id, integrationStatus: 'Validated' },
      });
      showToast(`Validation Passed for ${order.erpRef}`, 'success');
    }
  };

  // Action: Send to Consolidation
  const handleSendToConsolidation = (order) => {
    dispatch({ type: 'SET_ROUTE', payload: '/consolidation' });
    showToast(`Order ${order.id} transferred to Consolidation Planner`, 'info');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner & Action */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileSpreadsheet color="var(--primary-blue)" size={22} />
            ERP Order Intake Stream
          </h2>
          <p className="card-subtitle">
            Synchronised order intake from Accesco ERP Gateway with automated schema payload validation.
          </p>
        </div>

        <button className="tms-button tms-btn-primary" onClick={handleSimulateERPOrder}>
          <Plus size={16} /> Simulate ERP Order
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="tms-card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--secondary-text)' }} />
          <input
            type="text"
            className="tms-input"
            style={{ width: '100%', paddingLeft: '36px' }}
            placeholder="Search ERP ref, TMS ID, destination..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select className="tms-select" value={integrationFilter} onChange={(e) => setIntegrationFilter(e.target.value)}>
          <option value="All">All Integration Statuses</option>
          <option value="Validated">Validated</option>
          <option value="Received">Received</option>
          <option value="Validation Failed">Validation Failed</option>
          <option value="Duplicate">Duplicate</option>
        </select>

        <select className="tms-select" value={originFilter} onChange={(e) => setOriginFilter(e.target.value)}>
          <option value="All">All Origin Hubs</option>
          <option value="BGL-CENTRAL">Bengaluru Central Hub</option>
          <option value="BGL-NORTH">Bengaluru North Hub</option>
          <option value="HYD-HUB">Hyderabad Hub</option>
          <option value="CHN-HUB">Chennai Hub</option>
          <option value="MUM-HUB">Mumbai Hub</option>
        </select>

        <select className="tms-select" value={allocationFilter} onChange={(e) => setAllocationFilter(e.target.value)}>
          <option value="All">All Allocation States</option>
          <option value="Unallocated">Unallocated</option>
          <option value="Allocated">Allocated</option>
        </select>
      </div>

      {/* Orders Table */}
      <div className="tms-table-container">
        <table className="tms-table">
          <thead>
            <tr>
              <th>ERP Reference</th>
              <th>Internal TMS ID</th>
              <th>Origin Hub</th>
              <th>Destination</th>
              <th>Weight / Volume</th>
              <th>Delivery Window</th>
              <th>Priority</th>
              <th>Integration</th>
              <th>Allocation</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedOrders.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '32px', color: 'var(--secondary-text)' }}>
                  No matching ERP orders found
                </td>
              </tr>
            ) : (
              paginatedOrders.map((o) => (
                <tr key={o.id}>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{o.erpRef}</td>
                  <td style={{ fontWeight: '600' }}>{o.id}</td>
                  <td>{o.originName}</td>
                  <td>
                    <div style={{ fontWeight: '600' }}>{o.destinationName}</div>
                    <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>{o.destinationZone}</div>
                  </td>
                  <td>
                    <div style={{ fontWeight: '600' }}>{o.weightKg.toLocaleString()} kg</div>
                    <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>{o.volumeCbm} CBM</div>
                  </td>
                  <td style={{ fontSize: '12px' }}>
                    <div>{o.windowStart.replace('T', ' ')}</div>
                    <div style={{ color: 'var(--secondary-text)' }}>to {o.windowEnd.split('T')[1]}</div>
                  </td>
                  <td>
                    <span style={{ fontWeight: '600', color: o.priority === 'High' ? '#ef4444' : '#2563eb' }}>
                      {o.priority}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={o.integrationStatus} />
                  </td>
                  <td>
                    <StatusBadge status={o.allocationStatus} />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '6px' }}>
                      <button
                        className="tms-button tms-btn-secondary tms-btn-sm"
                        onClick={() => setSelectedOrderPayload(o)}
                        title="View API Payload"
                      >
                        <Code size={13} /> Payload
                      </button>

                      {o.allocationStatus === 'Unallocated' && (
                        <button
                          className="tms-button tms-btn-primary tms-btn-sm"
                          onClick={() => handleSendToConsolidation(o)}
                          title="Transfer to Consolidation"
                        >
                          Consolidate <ArrowRight size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={filteredOrders.length}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
        />
      </div>

      {/* Payload Drawer */}
      {selectedOrderPayload && (
        <Drawer
          title={`ERP Payload: ${selectedOrderPayload.erpRef}`}
          isOpen={!!selectedOrderPayload}
          onClose={() => setSelectedOrderPayload(null)}
          width="560px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="tms-card" style={{ padding: '14px', background: 'var(--bg-color)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="card-subtitle">Integration Status</span>
                <StatusBadge status={selectedOrderPayload.integrationStatus} />
              </div>
              <div style={{ fontSize: '12px', marginTop: '6px', color: 'var(--secondary-text)' }}>
                Ingested at: {selectedOrderPayload.integrationTimestamp} via REST API Gateway
              </div>
            </div>

            {/* Validation Rules Checklist */}
            <div className="tms-card" style={{ padding: '14px' }}>
              <div className="card-title" style={{ fontSize: '13px', marginBottom: '8px' }}>
                <ShieldCheck size={16} color="#16a34a" /> Schema & Business Rules Validation
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#16a34a' }}>
                  <CheckCircle2 size={14} /> ERP Reference Present ({selectedOrderPayload.erpRef})
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#16a34a' }}>
                  <CheckCircle2 size={14} /> Origin Complex Verified ({selectedOrderPayload.originComplexId})
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#16a34a' }}>
                  <CheckCircle2 size={14} /> Destination GPS Verified ({selectedOrderPayload.lat}, {selectedOrderPayload.lng})
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#16a34a' }}>
                  <CheckCircle2 size={14} /> Weight & Volume Above Zero ({selectedOrderPayload.weightKg} kg, {selectedOrderPayload.volumeCbm} CBM)
                </div>
              </div>
            </div>

            {/* JSON Code Viewer */}
            <div>
              <div className="card-subtitle" style={{ marginBottom: '6px' }}>Raw JSON Event Stream Payload</div>
              <pre
                style={{
                  backgroundColor: '#0f172a',
                  color: '#38bdf8',
                  padding: '16px',
                  borderRadius: '10px',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  overflowX: 'auto',
                }}
              >
                {JSON.stringify(
                  {
                    eventHeader: {
                      eventId: `EVT-${Date.now()}`,
                      channel: 'order-events',
                      sourceSystem: 'Accesco-ERP-Central',
                      timestamp: selectedOrderPayload.integrationTimestamp,
                    },
                    payload: selectedOrderPayload,
                  },
                  null,
                  2
                )}
              </pre>
            </div>
          </div>
        </Drawer>
      )}
    </div>
  );
}
