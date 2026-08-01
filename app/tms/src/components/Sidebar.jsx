import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Package,
  Boxes,
  Truck,
  Route,
  Handshake,
  Workflow,
  Gavel,
  Navigation,
  FileCheck,
  BarChart3,
  ShieldCheck,
  Network,
  AlertTriangle,
  Settings,
  Menu,
  X,
  Shield
} from 'lucide-react';
import styles from '../styles/sidebar.module.css';

export default function Sidebar({ isCollapsed, onToggleCollapse, onOpenIsoModal }) {
  const { state, dispatch } = useTMS();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigateTo = (path) => {
    dispatch({ type: 'SET_ROUTE', payload: path });
    setMobileOpen(false);
  };

  // Badge counters from state
  const unallocatedCount = state.orders.filter(o => o.allocationStatus === 'Unallocated').length;
  const activeShipmentsCount = state.shipments.filter(s => ['In Transit', 'Tendering', 'Carrier Assigned', 'Planned'].includes(s.shipmentStatus)).length;
  const activeTendersCount = state.tenders.filter(t => t.status === 'Active').length;
  const unreadAlertsCount = state.alerts.filter(a => a.readStatus === 'Unread').length;

  const navItems = [
    { label: 'Control Center', path: '/', icon: LayoutDashboard },
    { label: 'ERP Order Intake', path: '/erp-orders', icon: FileSpreadsheet, badge: unallocatedCount || 24 },
    { label: 'Orders & Shipments', path: '/shipments', icon: Package, badge: activeShipmentsCount || 142 },
    { label: 'Consolidation Planner', path: '/consolidation', icon: Boxes },
    { label: 'Capacity & Assets', path: '/capacity', icon: Truck },
    { label: 'Route Planning', path: '/route-planning', icon: Route },
    { label: 'Carrier Management', path: '/carriers', icon: Handshake },
    { label: 'Tender Waterfall', path: '/tenders', icon: Workflow, badge: activeTendersCount || 8 },
    { label: 'Spot Auctions', path: '/spot-auctions', icon: Gavel },
    { label: 'Live Tracking', path: '/tracking', icon: Navigation },
    { label: 'Freight Audit', path: '/freight-audit', icon: FileCheck },
    { label: 'Analytics & Reports', path: '/analytics', icon: BarChart3 },
    { label: 'Compliance & Audit', path: '/compliance', icon: ShieldCheck },
    { label: 'Integration Monitor', path: '/integrations', icon: Network },
    { label: 'Alerts & Exceptions', path: '/alerts', icon: AlertTriangle, badge: unreadAlertsCount || 6, badgeDanger: unreadAlertsCount > 0 },
    { label: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile drawer backdrop */}
      {mobileOpen && (
        <div className={styles.mobileBackdrop} onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar container */}
      <aside
        className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ''} ${
          mobileOpen ? styles.mobileOpen : ''
        }`}
      >
        {/* Header */}
        <div className={styles.sidebarHeader}>
          <button
            className={styles.toggleBtn}
            onClick={onToggleCollapse}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label="Toggle Navigation Sidebar"
          >
            <Menu size={18} />
          </button>

          <div className={styles.brandContainer} onClick={() => navigateTo('/')}>
            <div className={styles.logoSquare}>A</div>
            {!isCollapsed && (
              <div className={styles.brandTitles}>
                <div className={styles.brandName}>Accesco Living TMS</div>
                <div className={styles.brandSub}>Control Center</div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation List */}
        <nav className={styles.navScroll}>
          {navItems.map((item) => {
            const IconComponent = item.icon;
            const isActive = state.currentRoute === item.path;

            return (
              <button
                key={item.path}
                className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                onClick={() => navigateTo(item.path)}
                title={isCollapsed ? item.label : undefined}
              >
                <span className={styles.navIcon}>
                  <IconComponent size={18} />
                </span>

                {!isCollapsed && <span className={styles.navLabel}>{item.label}</span>}

                {!isCollapsed && item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`${styles.navBadge} ${
                      item.badgeDanger ? styles.navBadgeDanger : ''
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom ISO 9001 Compliance Card */}
        {!isCollapsed && (
          <div className={styles.complianceCard}>
            <div className={styles.complianceCardHeader}>
              <div className={styles.shieldIconWrapper}>
                <Shield size={16} />
              </div>
              <span className={styles.isoTitle}>ISO 9001 Certified</span>
            </div>
            <p className={styles.isoDesc}>
              Operational controls aligned with enterprise quality standards.
            </p>
            <button className={styles.isoBtn} onClick={onOpenIsoModal}>
              View Certificate
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
