import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import Pagination from '../components/Pagination';
import ConfirmDialog from '../components/ConfirmDialog';
import {
  Package,
  Truck,
  Eye,
  Edit,
  Trash2,
  Copy,
  Boxes,
  Workflow,
  Navigation,
  CheckCircle2,
  MapPin,
  Search
} from 'lucide-react';

export default function OrdersAndShipments() {
  const { state, dispatch, showToast } = useTMS();
  const [activeTab, setActiveTab] = useState('shipments'); // 'orders' or 'shipments'
  const [search, setSearch] = useState('');
  const [selectedShipmentDetail, setSelectedShipmentDetail] = useState(null);

  const [confirmCancelShipment, setConfirmCancelShipment] = useState(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Filter Shipments
  const filteredShipments = state.shipments.filter((s) => {
    return (
      s.id.toLowerCase().includes(search.toLowerCase()) ||
      s.origin.toLowerCase().includes(search.toLowerCase()) ||
      s.carrierName?.toLowerCase().includes(search.toLowerCase()) ||
      s.destinationZone.toLowerCase().includes(search.toLowerCase())
    );
  });

  // Filter Orders
  const filteredOrders = state.orders.filter((o) => {
    return (
      o.id.toLowerCase().includes(search.toLowerCase()) ||
      o.erpRef.toLowerCase().includes(search.toLowerCase()) ||
      o.destinationName.toLowerCase().includes(search.toLowerCase())
    );
  });

  const handleStartTender = (shipment) => {
    dispatch({ type: 'SET_ROUTE', payload: '/tenders' });
    showToast(`Navigated to Tender Waterfall for shipment ${shipment.id}`, 'info');
  };

  const handleTrack = (shipment) => {
    dispatch({ type: 'SET_ROUTE', payload: '/tracking' });
    showToast(`Navigated to Live Tracking for shipment ${shipment.id}`, 'info');
  };

  const handleMarkDelivered = (shipment) => {
    dispatch({
      type: 'ADD_TELEMETRY_EVENT',
      payload: {
        telemetry: {
          id: `TLM-${Date.now()}`,
          shipmentId: shipment.id,
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
          lat: 18.7606,
          lng: 73.8636,
          speedKmh: 0,
          reeferTempC: null,
          eta: 'Delivered',
          etaDriftMins: 0,
          geofenceStatus: 'Delivered at Destination Dock',
          eventSource: 'Driver Mobile App',
          processingStatus: 'Processed',
        },
        updatedShipment: {
          id: shipment.id,
          shipmentStatus: 'Delivered',
        },
      },
    });
    showToast(`Shipment ${shipment.id} marked as DELIVERED. Available for Freight Audit.`, 'success');
  };

  const handleConfirmCancel = () => {
    if (!confirmCancelShipment) return;
    dispatch({
      type: 'ADD_TELEMETRY_EVENT',
      payload: {
        telemetry: {
          id: `TLM-${Date.now()}`,
          shipmentId: confirmCancelShipment.id,
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
          lat: 0,
          lng: 0,
          speedKmh: 0,
          reeferTempC: null,
          eta: 'Cancelled',
          etaDriftMins: 0,
          geofenceStatus: 'Shipment Cancelled',
          eventSource: 'Dispatch Admin',
          processingStatus: 'Processed',
        },
        updatedShipment: {
          id: confirmCancelShipment.id,
          shipmentStatus: 'Cancelled',
        },
      },
    });
    showToast(`Shipment ${confirmCancelShipment.id} has been cancelled`, 'warning');
    setConfirmCancelShipment(null);
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header & Tabs */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Package color="var(--primary-blue)" size={22} />
            Orders & Shipments Management
          </h2>
          <p className="card-subtitle">
            Unified view connecting raw ERP order line-items to active consolidated freight shipments.
          </p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-color)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <button
            className={`tms-button ${activeTab === 'shipments' ? 'tms-btn-primary' : 'tms-btn-secondary'}`}
            style={{ height: '32px', fontSize: '12px' }}
            onClick={() => setActiveTab('shipments')}
          >
            <Truck size={14} /> Shipments ({state.shipments.length})
          </button>
          <button
            className={`tms-button ${activeTab === 'orders' ? 'tms-btn-primary' : 'tms-btn-secondary'}`}
            style={{ height: '32px', fontSize: '12px' }}
            onClick={() => setActiveTab('orders')}
          >
            <Package size={14} /> ERP Orders ({state.orders.length})
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="tms-card" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--secondary-text)' }} />
          <input
            type="text"
            className="tms-input"
            style={{ width: '100%', paddingLeft: '36px' }}
            placeholder={`Search ${activeTab === 'shipments' ? 'shipment ID, carrier, zone...' : 'order ref, TMS ID...'}`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Shipments Table */}
      {activeTab === 'shipments' && (
        <div className="tms-table-container">
          <table className="tms-table">
            <thead>
              <tr>
                <th>Shipment ID</th>
                <th>Type</th>
                <th>Origin</th>
                <th>Destination Zone</th>
                <th>Weight / Cube</th>
                <th>Capacity Utilisation</th>
                <th>Carrier</th>
                <th>Procurement</th>
                <th>Shipment Status</th>
                <th>ETA</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredShipments.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{s.id}</td>
                  <td style={{ fontWeight: '600' }}>{s.shipmentType}</td>
                  <td>{s.origin}</td>
                  <td>{s.destinationZone}</td>
                  <td>
                    <div>{s.totalWeightKg.toLocaleString()} kg</div>
                    <div style={{ fontSize: '11px', color: 'var(--secondary-text)' }}>{s.totalVolumeCbm} CBM</div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '6px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, s.weightUtilPct || 50)}%`, height: '100%', background: s.weightUtilPct > 95 ? '#ef4444' : '#2563eb' }} />
                      </div>
                      <span style={{ fontSize: '11px', fontWeight: '700' }}>{s.weightUtilPct || 50}%</span>
                    </div>
                  </td>
                  <td>{s.carrierName || 'Unassigned'}</td>
                  <td>
                    <StatusBadge status={s.procurementStatus} />
                  </td>
                  <td>
                    <StatusBadge status={s.shipmentStatus} />
                  </td>
                  <td style={{ fontSize: '12px' }}>{s.eta}</td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '4px' }}>
                      <button
                        className="tms-button tms-btn-secondary tms-btn-sm"
                        onClick={() => setSelectedShipmentDetail(s)}
                        title="View Full Details"
                      >
                        <Eye size={12} /> View
                      </button>

                      {s.shipmentStatus === 'Planned' && (
                        <button
                          className="tms-button tms-btn-primary tms-btn-sm"
                          onClick={() => handleStartTender(s)}
                          title="Start Tender Waterfall"
                        >
                          <Workflow size={12} /> Tender
                        </button>
                      )}

                      {s.shipmentStatus === 'In Transit' && (
                        <button
                          className="tms-button tms-btn-secondary tms-btn-sm"
                          onClick={() => handleTrack(s)}
                          title="Track GPS"
                        >
                          <Navigation size={12} /> Track
                        </button>
                      )}

                      {s.shipmentStatus === 'In Transit' && (
                        <button
                          className="tms-button tms-btn-primary tms-btn-sm"
                          onClick={() => handleMarkDelivered(s)}
                          title="Mark Delivered"
                        >
                          <CheckCircle2 size={12} /> Delivered
                        </button>
                      )}

                      {s.shipmentStatus !== 'Delivered' && s.shipmentStatus !== 'Cancelled' && (
                        <button
                          className="tms-button tms-btn-outline-danger tms-btn-sm"
                          onClick={() => setConfirmCancelShipment(s)}
                          title="Cancel Shipment"
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Orders Table */}
      {activeTab === 'orders' && (
        <div className="tms-table-container">
          <table className="tms-table">
            <thead>
              <tr>
                <th>ERP Order Ref</th>
                <th>TMS ID</th>
                <th>Origin</th>
                <th>Destination Name</th>
                <th>Zone</th>
                <th>Weight / Volume</th>
                <th>Delivery Window</th>
                <th>Priority</th>
                <th>Allocation Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((o) => (
                <tr key={o.id}>
                  <td style={{ fontWeight: '700', color: 'var(--primary-blue)' }}>{o.erpRef}</td>
                  <td style={{ fontWeight: '600' }}>{o.id}</td>
                  <td>{o.originName}</td>
                  <td>{o.destinationName}</td>
                  <td>{o.destinationZone}</td>
                  <td>{o.weightKg} kg / {o.volumeCbm} CBM</td>
                  <td style={{ fontSize: '12px' }}>{o.windowStart.split('T')[0]} to {o.windowEnd.split('T')[0]}</td>
                  <td>{o.priority}</td>
                  <td>
                    <StatusBadge status={o.allocationStatus} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Shipment Details Modal */}
      {selectedShipmentDetail && (
        <Modal
          title={`Shipment Detail Inspector: ${selectedShipmentDetail.id}`}
          isOpen={!!selectedShipmentDetail}
          onClose={() => setSelectedShipmentDetail(null)}
          maxWidth="640px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="tms-card" style={{ padding: '12px' }}>
                <div className="card-subtitle">Shipment Type</div>
                <div style={{ fontWeight: '700', fontSize: '14px' }}>{selectedShipmentDetail.shipmentType}</div>
              </div>
              <div className="tms-card" style={{ padding: '12px' }}>
                <div className="card-subtitle">Assigned Carrier</div>
                <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--primary-blue)' }}>
                  {selectedShipmentDetail.carrierName || 'Unassigned'}
                </div>
              </div>
              <div className="tms-card" style={{ padding: '12px' }}>
                <div className="card-subtitle">Total Weight</div>
                <div style={{ fontWeight: '700', fontSize: '14px' }}>{selectedShipmentDetail.totalWeightKg} kg</div>
              </div>
              <div className="tms-card" style={{ padding: '12px' }}>
                <div className="card-subtitle">Total Volume</div>
                <div style={{ fontWeight: '700', fontSize: '14px' }}>{selectedShipmentDetail.totalVolumeCbm} CBM</div>
              </div>
            </div>

            {/* Included Orders */}
            <div className="tms-card" style={{ padding: '14px' }}>
              <div className="card-subtitle" style={{ marginBottom: '8px' }}>Included Order Line Items</div>
              {selectedShipmentDetail.orderIds?.length > 0 ? (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {selectedShipmentDetail.orderIds.map((id) => (
                    <span key={id} style={{ padding: '4px 8px', borderRadius: '6px', background: 'var(--bg-color)', border: '1px solid var(--border-color)', fontSize: '12px', fontWeight: '600' }}>
                      {id}
                    </span>
                  ))}
                </div>
              ) : (
                <span style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>No orders explicitly mapped</span>
              )}
            </div>

            {/* Route Stops */}
            <div className="tms-card" style={{ padding: '14px' }}>
              <div className="card-subtitle" style={{ marginBottom: '8px' }}>Route Stops Sequence</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {selectedShipmentDetail.stops?.map((st, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                    <MapPin size={14} color="#2563eb" />
                    <span style={{ fontWeight: '600' }}>Stop {idx + 1}: {st.name}</span>
                    <span className="card-subtitle">({st.type})</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="tms-button tms-btn-primary" onClick={() => setSelectedShipmentDetail(null)}>
                Close Inspector
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Confirm Cancel Dialog */}
      {confirmCancelShipment && (
        <ConfirmDialog
          isOpen={!!confirmCancelShipment}
          title="Cancel Shipment?"
          message={`Are you sure you want to cancel shipment ${confirmCancelShipment.id}? Included orders will be set back to Unallocated.`}
          confirmText="Cancel Shipment"
          isDanger={true}
          onConfirm={handleConfirmCancel}
          onClose={() => setConfirmCancelShipment(null)}
        />
      )}
    </div>
  );
}
