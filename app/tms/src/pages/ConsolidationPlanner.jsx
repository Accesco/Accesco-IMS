import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import StatusBadge from '../components/StatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import {
  Boxes,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Minus,
  Split,
  Combine,
  Truck,
  ArrowRight,
  RotateCw
} from 'lucide-react';

export default function ConsolidationPlanner() {
  const { state, dispatch, showToast } = useTMS();
  const [selectedGroupId, setSelectedGroupId] = useState(null);

  // Unallocated orders
  const unallocatedOrders = state.orders.filter(
    (o) => o.allocationStatus === 'Unallocated' && o.integrationStatus === 'Validated'
  );

  // Group unallocated orders by destination zone & temperature
  const generateSuggestedGroups = () => {
    const groups = [];
    const zoneMap = {};

    unallocatedOrders.forEach((order) => {
      const key = `${order.destinationZone}_${order.tempRequirement}`;
      if (!zoneMap[key]) zoneMap[key] = [];
      zoneMap[key].push(order);
    });

    let groupCounter = 1;
    Object.keys(zoneMap).forEach((key) => {
      const orderList = zoneMap[key];
      let currentWeight = 0;
      let currentVolume = 0;
      let currentOrders = [];

      orderList.forEach((ord) => {
        // Strict blueprint limit: Max 18,000 kg or Max 60.0 CBM
        if (
          currentWeight + ord.weightKg > 18000 ||
          currentVolume + ord.volumeCbm > 60.0
        ) {
          // Finalize current group
          if (currentOrders.length > 0) {
            const weightUtil = Number(((currentWeight / 18000) * 100).toFixed(1));
            const volumeUtil = Number(((currentVolume / 60.0) * 100).toFixed(1));
            groups.push({
              id: `CSG-${100 + groupCounter++}`,
              orders: currentOrders,
              zone: currentOrders[0].destinationZone,
              tempRequirement: currentOrders[0].tempRequirement,
              totalWeightKg: currentWeight,
              totalVolumeCbm: Number(currentVolume.toFixed(1)),
              weightUtilPct: weightUtil,
              volumeUtilPct: volumeUtil,
              recommendedVehicle:
                currentOrders[0].tempRequirement.includes('Reefer')
                  ? 'Reefer Truck (18T)'
                  : 'Heavy Container Truck (18T)',
              recommendedMode:
                currentOrders[0].tempRequirement.includes('Reefer')
                  ? 'Reefer'
                  : currentOrders.length > 1
                  ? 'Milk Run'
                  : 'FTL',
              isOver95: weightUtil > 95 || volumeUtil > 95,
              status: 'Suggested',
            });
          }
          currentWeight = ord.weightKg;
          currentVolume = ord.volumeCbm;
          currentOrders = [ord];
        } else {
          currentWeight += ord.weightKg;
          currentVolume += ord.volumeCbm;
          currentOrders.push(ord);
        }
      });

      if (currentOrders.length > 0) {
        const weightUtil = Number(((currentWeight / 18000) * 100).toFixed(1));
        const volumeUtil = Number(((currentVolume / 60.0) * 100).toFixed(1));
        groups.push({
          id: `CSG-${100 + groupCounter++}`,
          orders: currentOrders,
          zone: currentOrders[0].destinationZone,
          tempRequirement: currentOrders[0].tempRequirement,
          totalWeightKg: currentWeight,
          totalVolumeCbm: Number(currentVolume.toFixed(1)),
          weightUtilPct: weightUtil,
          volumeUtilPct: volumeUtil,
          recommendedVehicle:
            currentOrders[0].tempRequirement.includes('Reefer')
              ? 'Reefer Truck (18T)'
              : 'Heavy Container Truck (18T)',
          recommendedMode:
            currentOrders[0].tempRequirement.includes('Reefer')
              ? 'Reefer'
              : currentOrders.length > 1
              ? 'Milk Run'
              : 'FTL',
          isOver95: weightUtil > 95 || volumeUtil > 95,
          status: 'Suggested',
        });
      }
    });

    return groups;
  };

  const [suggestedGroups, setSuggestedGroups] = useState(generateSuggestedGroups());

  const selectedGroup =
    suggestedGroups.find((g) => g.id === selectedGroupId) || suggestedGroups[0];

  // Action: Auto Consolidate
  const handleAutoConsolidate = () => {
    const newGroups = generateSuggestedGroups();
    setSuggestedGroups(newGroups);
    showToast(
      `Auto Consolidation complete: Created ${newGroups.length} optimized shipment group(s) adhering to 18,000kg & 60CBM limits`,
      'success'
    );
  };

  // Action: Approve Consolidation
  const handleApproveConsolidation = (group) => {
    if (!group) return;

    const shipmentId = `SHP-${Math.floor(8800 + Math.random() * 1000)}`;
    const newShipment = {
      id: shipmentId,
      shipmentType: group.recommendedMode,
      orderIds: group.orders.map((o) => o.id),
      origin: group.orders[0].originName,
      destinationZone: group.zone,
      destinationName: group.orders[0].destinationName,
      stops: group.orders.map((o) => ({
        name: o.destinationName,
        type: 'Dropoff',
        lat: o.lat,
        lng: o.lng,
        deadline: o.windowEnd,
      })),
      totalWeightKg: group.totalWeightKg,
      totalVolumeCbm: group.totalVolumeCbm,
      weightUtilPct: group.weightUtilPct,
      volumeUtilPct: group.volumeUtilPct,
      assignedAssetId: 'AST-V01',
      carrierId: null,
      carrierName: 'Unassigned (Awaiting Tender)',
      procurementStatus: 'Contract Matching',
      shipmentStatus: 'Planned',
      eta: 'Pending Tender Award',
      etaDriftMins: 0,
      currentLat: group.orders[0].lat,
      currentLng: group.orders[0].lng,
      speedKmh: 0,
      reeferTempC: group.tempRequirement.includes('Reefer') ? 4.0 : null,
      isReefer: group.tempRequirement.includes('Reefer'),
      costSAR: group.totalWeightKg * 0.45,
    };

    const updatedOrders = state.orders.map((o) =>
      group.orders.some((gOrd) => gOrd.id === o.id)
        ? { ...o, allocationStatus: 'Allocated' }
        : o
    );

    const newAudits = [
      {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: 'Consolidation Planner Engine',
        module: 'Consolidation',
        action: 'Consolidation Group Approved',
        recordId: shipmentId,
        previousValue: `${group.orders.length} Unallocated Orders`,
        newValue: `Planned Shipment ${shipmentId} (${group.recommendedMode})`,
        severity: 'Info',
      },
    ];

    dispatch({
      type: 'AUTO_CONSOLIDATE',
      payload: {
        newShipments: [newShipment],
        updatedOrders,
        newAudits,
      },
    });

    setSuggestedGroups(suggestedGroups.filter((g) => g.id !== group.id));
    showToast(`Approved Consolidation: Created Shipment ${shipmentId}. Ready for Tender Waterfall!`, 'success');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div className="tms-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Boxes color="var(--primary-blue)" size={22} />
            Continuous Consolidation Planner
          </h2>
          <p className="card-subtitle">
            Combines LTL order streams into FTL & Milk-run schedules subject to 18,000 kg weight & 60.0 CBM cubic thresholds.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="tms-button tms-btn-secondary" onClick={handleAutoConsolidate}>
            <Sparkles size={16} color="#2563eb" /> Auto Consolidate
          </button>
        </div>
      </div>

      {/* Blueprint 4-Stage Workflow Indicator */}
      <div className="tms-card" style={{ padding: '14px 20px', background: 'var(--bg-color)' }}>
        <div className="card-subtitle" style={{ marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Accesco Living 4-Stage Optimization Algorithm
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          <div style={{ padding: '10px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--primary-blue)' }}>1. Constraint Sorting</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>Destination zone, window deadlines, cargo temperature</div>
          </div>
          <div style={{ padding: '10px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: '#16a34a' }}>2. Capacity Evaluation</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>Max 18,000 kg or Max 60.0 CBM limits</div>
          </div>
          <div style={{ padding: '10px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: '#8b5cf6' }}>3. Sequential Mapping</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>Stop ordering by zone proximity & delivery windows</div>
          </div>
          <div style={{ padding: '10px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '11px', fontWeight: '700', color: '#06b6d4' }}>4. Asset Provisioning</div>
            <div style={{ fontSize: '11px', color: 'var(--secondary-text)', marginTop: '2px' }}>Creates dedicated run if payload exceeds vehicle limits</div>
          </div>
        </div>
      </div>

      {/* 3-Panel Workspace */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr 1.2fr', gap: '16px' }}>
        {/* Left Panel: Available Unallocated Orders */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card-header-flex">
            <span className="card-title">Unallocated Orders ({unallocatedOrders.length})</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '520px', overflowY: 'auto' }}>
            {unallocatedOrders.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px', fontSize: '12px', color: 'var(--secondary-text)' }}>
                All validated orders have been consolidated into shipments.
              </div>
            ) : (
              unallocatedOrders.map((ord) => (
                <div
                  key={ord.id}
                  style={{
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '700', fontSize: '12px' }}>
                    <span style={{ color: 'var(--primary-blue)' }}>{ord.erpRef}</span>
                    <span>{ord.destinationZone}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--dark-text)', marginTop: '4px' }}>
                    {ord.weightKg} kg | {ord.volumeCbm} CBM
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--secondary-text)', marginTop: '2px' }}>
                    {ord.tempRequirement}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Centre Panel: Suggested Shipment Groups */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card-header-flex">
            <span className="card-title">Suggested Shipment Groups ({suggestedGroups.length})</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '520px', overflowY: 'auto' }}>
            {suggestedGroups.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px', fontSize: '12px', color: 'var(--secondary-text)' }}>
                No suggested groups. Click "Auto Consolidate" to generate schedules.
              </div>
            ) : (
              suggestedGroups.map((group) => {
                const isSelected = selectedGroup?.id === group.id;
                return (
                  <div
                    key={group.id}
                    onClick={() => setSelectedGroupId(group.id)}
                    style={{
                      padding: '14px',
                      borderRadius: '10px',
                      border: `2px solid ${isSelected ? 'var(--primary-blue)' : 'var(--border-color)'}`,
                      backgroundColor: isSelected ? 'rgba(37, 99, 235, 0.04)' : 'var(--card-bg)',
                      cursor: 'pointer',
                      transition: 'border-color 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: '700', fontSize: '14px', color: 'var(--dark-text)' }}>
                        {group.id} ({group.recommendedMode})
                      </span>
                      <StatusBadge status={group.zone} />
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--secondary-text)', marginTop: '4px' }}>
                      Orders Included: {group.orders.length} orders ({group.orders.map((o) => o.erpRef).join(', ')})
                    </div>

                    {/* Weight & Volume Utilisation Bars */}
                    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: '600' }}>
                          <span>Weight ({group.totalWeightKg.toLocaleString()} / 18,000 kg)</span>
                          <span>{group.weightUtilPct}%</span>
                        </div>
                        <div style={{ height: '6px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden', marginTop: '2px' }}>
                          <div
                            style={{
                              width: `${Math.min(100, group.weightUtilPct)}%`,
                              height: '100%',
                              background: group.weightUtilPct > 95 ? '#ef4444' : '#2563eb',
                            }}
                          />
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: '600' }}>
                          <span>Cube Volume ({group.totalVolumeCbm} / 60.0 CBM)</span>
                          <span>{group.volumeUtilPct}%</span>
                        </div>
                        <div style={{ height: '6px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden', marginTop: '2px' }}>
                          <div
                            style={{
                              width: `${Math.min(100, group.volumeUtilPct)}%`,
                              height: '100%',
                              background: group.volumeUtilPct > 95 ? '#ef4444' : '#06b6d4',
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    {group.isOver95 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#d97706', marginTop: '8px', fontWeight: '600' }}>
                        <AlertTriangle size={14} /> Warning: Near maximum capacity threshold (&gt;95%)
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Panel: Selected Group Summary & Actions */}
        <div className="tms-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="card-header-flex">
            <span className="card-title">Selected Group Summary</span>
          </div>

          {selectedGroup ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '12px', background: 'var(--bg-color)', borderRadius: '8px' }}>
                <div className="card-subtitle">Recommended Mode</div>
                <div style={{ fontSize: '15px', fontWeight: '700', color: 'var(--primary-blue)', marginTop: '2px' }}>
                  {selectedGroup.recommendedMode}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--secondary-text)' }}>
                  Vehicle: {selectedGroup.recommendedVehicle}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ padding: '8px', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <div className="card-subtitle">Total Weight</div>
                  <div style={{ fontWeight: '700', fontSize: '13px' }}>{selectedGroup.totalWeightKg.toLocaleString()} kg</div>
                </div>
                <div style={{ padding: '8px', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <div className="card-subtitle">Total Cube</div>
                  <div style={{ fontWeight: '700', fontSize: '13px' }}>{selectedGroup.totalVolumeCbm} CBM</div>
                </div>
              </div>

              <div>
                <div className="card-subtitle" style={{ marginBottom: '6px' }}>Included Order References</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {selectedGroup.orders.map((o) => (
                    <div key={o.id} style={{ fontSize: '12px', padding: '6px 8px', background: 'var(--bg-color)', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: '600' }}>{o.erpRef}</span>
                      <span>{o.weightKg} kg</span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                className="tms-button tms-btn-primary"
                style={{ marginTop: '12px', width: '100%', height: '40px' }}
                onClick={() => handleApproveConsolidation(selectedGroup)}
              >
                <CheckCircle2 size={16} /> Approve & Generate Shipment
              </button>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--secondary-text)', fontSize: '12px' }}>
              Select a group from the center panel to review payload summary.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
