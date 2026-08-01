import React, { createContext, useContext, useReducer, useEffect } from 'react';
import {
  INITIAL_ORDERS,
  INITIAL_SHIPMENTS,
  INITIAL_CARRIERS,
  INITIAL_TARIFFS,
  INITIAL_ASSETS,
  INITIAL_TENDERS,
  INITIAL_AUCTIONS,
  INITIAL_BIDS,
  INITIAL_TELEMETRY,
  INITIAL_INVOICES,
  INITIAL_ALERTS,
  INITIAL_AUDIT_LOGS,
  INITIAL_INTEGRATIONS,
  INITIAL_SETTINGS,
} from '../data/mockData';

const LOCAL_STORAGE_KEY = 'accesco_tms_state_v1';

const TMSContext = createContext();

const initialState = {
  orders: INITIAL_ORDERS,
  shipments: INITIAL_SHIPMENTS,
  carriers: INITIAL_CARRIERS,
  tariffs: INITIAL_TARIFFS,
  assets: INITIAL_ASSETS,
  tenders: INITIAL_TENDERS,
  auctions: INITIAL_AUCTIONS,
  bids: INITIAL_BIDS,
  telemetry: INITIAL_TELEMETRY,
  telemetryEvents: INITIAL_TELEMETRY,
  invoices: INITIAL_INVOICES,
  alerts: INITIAL_ALERTS,
  auditLogs: INITIAL_AUDIT_LOGS,
  integrations: INITIAL_INTEGRATIONS,
  settings: INITIAL_SETTINGS,
  filters: {
    dateRange: 'Last 30 Days',
    originComplex: 'All Origin Complexes',
    destinationZone: 'All Zones',
    carrier: 'All Carriers',
    shipmentStatus: 'All Statuses',
    transportMode: 'All Modes',
    procurementStatus: 'All Procurement Statuses',
    businessVertical: 'All Verticals',
    searchQuery: '',
  },
  currentRoute: '/',
  activeModal: null,
  toast: null,
  lastRefreshed: new Date().toLocaleTimeString(),
};

function tmsReducer(state, action) {
  switch (action.type) {
    case 'SET_ROUTE':
      return { ...state, currentRoute: action.payload };

    case 'SET_FILTERS':
      return { ...state, filters: { ...state.filters, ...action.payload } };

    case 'RESET_FILTERS':
      return {
        ...state,
        filters: {
          dateRange: 'Last 30 Days',
          originComplex: 'All Origin Complexes',
          destinationZone: 'All Zones',
          carrier: 'All Carriers',
          shipmentStatus: 'All Statuses',
          transportMode: 'All Modes',
          procurementStatus: 'All Procurement Statuses',
          businessVertical: 'All Verticals',
          searchQuery: '',
        },
      };

    case 'SHOW_TOAST':
      return { ...state, toast: action.payload };

    case 'HIDE_TOAST':
      return { ...state, toast: null };

    case 'OPEN_MODAL':
      return { ...state, activeModal: action.payload };

    case 'CLOSE_MODAL':
      return { ...state, activeModal: null };

    case 'REFRESH_DASHBOARD':
      return {
        ...state,
        lastRefreshed: new Date().toLocaleTimeString(),
      };

    case 'SIMULATE_ERP_ORDER': {
      const newOrder = action.payload;
      const newAudit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: 'ERP API Gateway',
        module: 'ERP Intake',
        action: 'ERP Order Received',
        recordId: newOrder.id,
        previousValue: 'N/A',
        newValue: `ERP Ref ${newOrder.erpRef} (Unallocated)`,
        severity: 'Info',
      };
      return {
        ...state,
        orders: [newOrder, ...state.orders],
        auditLogs: [newAudit, ...state.auditLogs],
      };
    }

    case 'UPDATE_ORDER_STATUS': {
      const { orderId, allocationStatus, integrationStatus } = action.payload;
      return {
        ...state,
        orders: state.orders.map((o) =>
          o.id === orderId
            ? {
                ...o,
                ...(allocationStatus && { allocationStatus }),
                ...(integrationStatus && { integrationStatus }),
              }
            : o
        ),
      };
    }

    case 'AUTO_CONSOLIDATE': {
      const { newShipments, updatedOrders, newAudits } = action.payload;
      return {
        ...state,
        shipments: [...newShipments, ...state.shipments],
        orders: updatedOrders,
        auditLogs: [...newAudits, ...state.auditLogs],
      };
    }

    case 'APPROVE_CONSOLIDATION': {
      const { shipmentId } = action.payload;
      const targetShipment = state.shipments.find((s) => s.id === shipmentId);
      if (!targetShipment) return state;

      const updatedShipments = state.shipments.map((s) =>
        s.id === shipmentId
          ? { ...s, shipmentStatus: 'Planned', procurementStatus: 'Contract Matching' }
          : s
      );

      const updatedOrders = state.orders.map((o) =>
        targetShipment.orderIds.includes(o.id)
          ? { ...o, allocationStatus: 'Allocated' }
          : o
      );

      const audit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: 'Consolidation Planner',
        module: 'Consolidation',
        action: 'Consolidation Approved',
        recordId: shipmentId,
        previousValue: 'Draft Group',
        newValue: 'Planned Shipment (Ready for Tender)',
        severity: 'Info',
      };

      return {
        ...state,
        shipments: updatedShipments,
        orders: updatedOrders,
        auditLogs: [audit, ...state.auditLogs],
      };
    }

    case 'DISPATCH_TENDER': {
      const { tender } = action.payload;
      return {
        ...state,
        tenders: [tender, ...state.tenders],
        shipments: state.shipments.map((s) =>
          s.id === tender.shipmentId
            ? { ...s, procurementStatus: 'Awaiting Response', shipmentStatus: 'Tendering' }
            : s
        ),
      };
    }

    case 'TENDER_ACCEPT': {
      const { tenderId } = action.payload;
      const targetTender = state.tenders.find((t) => t.id === tenderId);
      if (!targetTender) return state;

      const updatedTenders = state.tenders.map((t) =>
        t.id === tenderId ? { ...t, response: 'Accepted', status: 'Completed' } : t
      );

      const updatedShipments = state.shipments.map((s) =>
        s.id === targetTender.shipmentId
          ? {
              ...s,
              carrierId: targetTender.carrierId,
              carrierName: targetTender.carrierName,
              procurementStatus: 'Accepted',
              shipmentStatus: 'Carrier Assigned',
              costSAR: targetTender.contractedRateSAR,
            }
          : s
      );

      const audit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: targetTender.carrierName,
        module: 'Tender Waterfall',
        action: 'Tender Accepted',
        recordId: targetTender.shipmentId,
        previousValue: 'Awaiting Response',
        newValue: `Assigned to ${targetTender.carrierName}`,
        severity: 'Info',
      };

      return {
        ...state,
        tenders: updatedTenders,
        shipments: updatedShipments,
        auditLogs: [audit, ...state.auditLogs],
      };
    }

    case 'TENDER_REJECT': {
      const { tenderId, reason } = action.payload;
      const targetTender = state.tenders.find((t) => t.id === tenderId);
      if (!targetTender) return state;

      const updatedTenders = state.tenders.map((t) =>
        t.id === tenderId ? { ...t, response: 'Rejected', status: 'Failed' } : t
      );

      const audit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: targetTender.carrierName,
        module: 'Tender Waterfall',
        action: 'Tender Rejected',
        recordId: targetTender.shipmentId,
        previousValue: 'Awaiting Response',
        newValue: `Rejected (${reason || 'Capacity constraint'})`,
        severity: 'Warning',
      };

      return {
        ...state,
        tenders: updatedTenders,
        auditLogs: [audit, ...state.auditLogs],
      };
    }

    // MANDATORY RULE: Tender Timeout reduces carrier tier score by 2.5%!
    case 'TENDER_TIMEOUT': {
      const { tenderId } = action.payload;
      const targetTender = state.tenders.find((t) => t.id === tenderId);
      if (!targetTender) return state;

      const carrier = state.carriers.find((c) => c.id === targetTender.carrierId);
      const oldScore = carrier ? carrier.tierScorePct : 90.0;
      const newScore = Math.max(0, Number((oldScore - 2.5).toFixed(1)));

      const updatedCarriers = state.carriers.map((c) =>
        c.id === targetTender.carrierId
          ? {
              ...c,
              tierScorePct: newScore,
              slaBreaches: (c.slaBreaches || 0) + 1,
              tenderAcceptanceRatePct: Math.max(0, Number((c.tenderAcceptanceRatePct - 1.5).toFixed(1))),
            }
          : c
      );

      const updatedTenders = state.tenders.map((t) =>
        t.id === tenderId ? { ...t, response: 'Timed Out', status: 'Timed Out' } : t
      );

      const newAlert = {
        id: `ALT-${Date.now()}`,
        type: 'Tender Timeout Penalty',
        relatedRecordId: targetTender.carrierId,
        severity: 'High',
        message: `Tender invitation timed out for carrier ${targetTender.carrierName} on ${targetTender.shipmentId}. 2.5% performance penalty applied (${oldScore}% -> ${newScore}%).`,
        createdTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
        readStatus: 'Unread',
        resolutionStatus: 'Open',
        assignedTo: 'Procurement Ops',
      };

      const newAudit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: 'System Waterfall Monitor',
        module: 'Tender Waterfall',
        action: 'Tender Timeout Breach (-2.5% Score Penalty)',
        recordId: targetTender.carrierId,
        previousValue: `Tier Score ${oldScore}%`,
        newValue: `Tier Score ${newScore}%`,
        severity: 'Warning',
      };

      return {
        ...state,
        carriers: updatedCarriers,
        tenders: updatedTenders,
        alerts: [newAlert, ...state.alerts],
        auditLogs: [newAudit, ...state.auditLogs],
      };
    }

    case 'CREATE_SPOT_AUCTION': {
      const { auction } = action.payload;
      return {
        ...state,
        auctions: [auction, ...state.auctions],
        shipments: state.shipments.map((s) =>
          s.id === auction.shipmentId ? { ...s, procurementStatus: 'Spot Auction' } : s
        ),
      };
    }

    case 'SUBMIT_SPOT_BID': {
      const { bid } = action.payload;
      const updatedAuctions = state.auctions.map((a) => {
        if (a.id === bid.auctionId) {
          const isLower = !a.currentLowestBidSAR || bid.bidAmountSAR < a.currentLowestBidSAR;
          return {
            ...a,
            totalBidsCount: (a.totalBidsCount || 0) + 1,
            ...(isLower && {
              currentLowestBidSAR: bid.bidAmountSAR,
              lowestBidderCarrierName: bid.carrierName,
            }),
          };
        }
        return a;
      });

      return {
        ...state,
        bids: [bid, ...state.bids],
        auctions: updatedAuctions,
      };
    }

    case 'AWARD_SPOT_AUCTION': {
      const { auctionId, winningBidId } = action.payload;
      const targetAuction = state.auctions.find((a) => a.id === auctionId);
      const winningBid = state.bids.find((b) => b.id === winningBidId);

      if (!targetAuction || !winningBid) return state;

      const updatedAuctions = state.auctions.map((a) =>
        a.id === auctionId ? { ...a, status: 'Awarded' } : a
      );

      const updatedShipments = state.shipments.map((s) =>
        s.id === targetAuction.shipmentId
          ? {
              ...s,
              carrierId: winningBid.carrierId,
              carrierName: winningBid.carrierName,
              procurementStatus: 'Accepted',
              shipmentStatus: 'Carrier Assigned',
              costSAR: winningBid.bidAmountSAR,
            }
          : s
      );

      const audit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: 'Spot Auction Engine',
        module: 'Spot Auctions',
        action: 'Spot Auction Awarded',
        recordId: targetAuction.shipmentId,
        previousValue: 'Spot Auction',
        newValue: `Awarded to ${winningBid.carrierName} @ SAR ${winningBid.bidAmountSAR}`,
        severity: 'Info',
      };

      return {
        ...state,
        auctions: updatedAuctions,
        shipments: updatedShipments,
        auditLogs: [audit, ...state.auditLogs],
      };
    }

    case 'ESCALATE_HUMAN_DISPATCH': {
      const { shipmentId, reason } = action.payload;
      const updatedShipments = state.shipments.map((s) =>
        s.id === shipmentId ? { ...s, procurementStatus: 'Human Dispatch' } : s
      );

      const newAlert = {
        id: `ALT-${Date.now()}`,
        type: 'Human Dispatch Escalation',
        relatedRecordId: shipmentId,
        severity: 'Critical',
        message: `Shipment ${shipmentId} requires immediate human dispatch. Reason: ${reason}`,
        createdTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
        readStatus: 'Unread',
        resolutionStatus: 'Open',
        assignedTo: 'Senior Dispatcher',
      };

      return {
        ...state,
        shipments: updatedShipments,
        alerts: [newAlert, ...state.alerts],
      };
    }

    case 'ADD_TELEMETRY_EVENT': {
      const { telemetry, updatedShipment, alert } = action.payload;
      const updatedShipments = state.shipments.map((s) =>
        s.id === updatedShipment.id ? { ...s, ...updatedShipment } : s
      );

      return {
        ...state,
        telemetry: [telemetry, ...(state.telemetry || [])],
        telemetryEvents: [telemetry, ...(state.telemetryEvents || state.telemetry || [])],
        shipments: updatedShipments,
        ...(alert && { alerts: [alert, ...state.alerts] }),
      };
    }

    case 'ADD_FREIGHT_INVOICE': {
      return {
        ...state,
        invoices: [action.payload, ...state.invoices],
      };
    }

    case 'AUDIT_FREIGHT_INVOICE': {
      const { invoiceId, auditStatus, paymentStatus, auditResult } = action.payload;
      const updatedInvoices = state.invoices.map((inv) =>
        inv.id === invoiceId
          ? {
              ...inv,
              auditStatus,
              paymentStatus,
              ...(auditResult && { auditResult }),
            }
          : inv
      );

      const audit = {
        id: `AUD-${Date.now()}`,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user: 'Freight Audit Engine',
        module: 'Freight Audit',
        action: 'Three-Way Invoice Verification',
        recordId: invoiceId,
        previousValue: 'Awaiting Review',
        newValue: auditStatus,
        severity: auditStatus === 'Passed' ? 'Info' : 'Warning',
      };

      return {
        ...state,
        invoices: updatedInvoices,
        auditLogs: [audit, ...state.auditLogs],
      };
    }

    case 'MARK_ALERT_READ': {
      return {
        ...state,
        alerts: state.alerts.map((a) => (a.id === action.payload ? { ...a, readStatus: 'Read' } : a)),
      };
    }

    case 'MARK_ALL_ALERTS_READ': {
      return {
        ...state,
        alerts: state.alerts.map((a) => ({ ...a, readStatus: 'Read' })),
      };
    }

    case 'RESOLVE_ALERT': {
      return {
        ...state,
        alerts: state.alerts.map((a) =>
          a.id === action.payload ? { ...a, resolutionStatus: 'Resolved', readStatus: 'Read' } : a
        ),
      };
    }

    case 'ADD_ASSET': {
      return {
        ...state,
        assets: [action.payload, ...state.assets],
      };
    }

    case 'UPDATE_ASSET': {
      return {
        ...state,
        assets: state.assets.map((a) => (a.id === action.payload.id ? { ...a, ...action.payload } : a)),
      };
    }

    case 'ADD_CARRIER': {
      return {
        ...state,
        carriers: [action.payload, ...state.carriers],
      };
    }

    case 'UPDATE_CARRIER': {
      return {
        ...state,
        carriers: state.carriers.map((c) => (c.id === action.payload.id ? { ...c, ...action.payload } : c)),
      };
    }

    case 'ADD_TARIFF': {
      return {
        ...state,
        tariffs: [action.payload, ...state.tariffs],
      };
    }

    case 'UPDATE_SETTINGS': {
      return {
        ...state,
        settings: { ...state.settings, ...action.payload },
      };
    }

    case 'RESET_DEMO_DATA': {
      return {
        ...initialState,
        lastRefreshed: new Date().toLocaleTimeString(),
      };
    }

    case 'LOAD_PERSISTED_STATE': {
      return {
        ...state,
        ...action.payload,
      };
    }

    default:
      return state;
  }
}

export function TMSProvider({ children }) {
  const [state, dispatch] = useReducer(tmsReducer, initialState);

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        dispatch({ type: 'LOAD_PERSISTED_STATE', payload: parsed });
      }
    } catch (e) {
      console.warn('Failed to parse saved TMS state:', e);
    }
  }, []);

  // Save state to localStorage on updates
  useEffect(() => {
    try {
      const toSave = {
        orders: state.orders,
        shipments: state.shipments,
        carriers: state.carriers,
        tariffs: state.tariffs,
        assets: state.assets,
        tenders: state.tenders,
        auctions: state.auctions,
        bids: state.bids,
        telemetry: state.telemetry,
        invoices: state.invoices,
        alerts: state.alerts,
        auditLogs: state.auditLogs,
        integrations: state.integrations,
        settings: state.settings,
      };
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(toSave));
    } catch (e) {
      console.warn('Failed to persist TMS state:', e);
    }
  }, [
    state.orders,
    state.shipments,
    state.carriers,
    state.tariffs,
    state.assets,
    state.tenders,
    state.auctions,
    state.bids,
    state.telemetry,
    state.invoices,
    state.alerts,
    state.auditLogs,
    state.integrations,
    state.settings,
  ]);

  // Dark mode effect
  useEffect(() => {
    if (state.settings.darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [state.settings.darkMode]);

  const showToast = (message, type = 'success') => {
    dispatch({ type: 'SHOW_TOAST', payload: { message, type, id: Date.now() } });
  };

  const hideToast = () => {
    dispatch({ type: 'HIDE_TOAST' });
  };

  return (
    <TMSContext.Provider value={{ state, dispatch, showToast, hideToast }}>
      {children}
    </TMSContext.Provider>
  );
}

export function useTMS() {
  const context = useContext(TMSContext);
  if (!context) {
    throw new Error('useTMS must be used within a TMSProvider');
  }
  return context;
}
