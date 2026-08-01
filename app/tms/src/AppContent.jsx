import React, { useState } from 'react';
import { useTMS } from './context/TMSContext';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Toast from './components/Toast';
import IsoCertificateModal from './components/IsoCertificateModal';

// Pages
import ControlCenter from './pages/ControlCenter';
import ERPOrderIntake from './pages/ERPOrderIntake';
import OrdersAndShipments from './pages/OrdersAndShipments';
import ConsolidationPlanner from './pages/ConsolidationPlanner';
import CapacityAndAssets from './pages/CapacityAndAssets';
import RoutePlanning from './pages/RoutePlanning';
import CarrierManagement from './pages/CarrierManagement';
import TenderWaterfall from './pages/TenderWaterfall';
import SpotAuctions from './pages/SpotAuctions';
import LiveTracking from './pages/LiveTracking';
import FreightAudit from './pages/FreightAudit';
import AnalyticsAndReports from './pages/AnalyticsAndReports';
import ComplianceAndAudit from './pages/ComplianceAndAudit';
import IntegrationMonitor from './pages/IntegrationMonitor';
import AlertsAndExceptions from './pages/AlertsAndExceptions';
import Settings from './pages/Settings';

export default function AppContent() {
  const { state, dispatch } = useTMS();
  const [isIsoModalOpen, setIsIsoModalOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const renderCurrentRoute = () => {
    switch (state.currentRoute) {
      case '/':
        return <ControlCenter />;
      case '/erp-orders':
        return <ERPOrderIntake />;
      case '/shipments':
        return <OrdersAndShipments />;
      case '/consolidation':
        return <ConsolidationPlanner />;
      case '/capacity':
        return <CapacityAndAssets />;
      case '/route-planning':
        return <RoutePlanning />;
      case '/carriers':
        return <CarrierManagement />;
      case '/tenders':
        return <TenderWaterfall />;
      case '/spot-auctions':
        return <SpotAuctions />;
      case '/tracking':
        return <LiveTracking />;
      case '/freight-audit':
        return <FreightAudit />;
      case '/analytics':
        return <AnalyticsAndReports />;
      case '/compliance':
        return <ComplianceAndAudit />;
      case '/integrations':
        return <IntegrationMonitor />;
      case '/alerts':
        return <AlertsAndExceptions />;
      case '/settings':
        return <Settings />;
      default:
        return <ControlCenter />;
    }
  };

  return (
    <div className={`app-container ${state.darkMode ? 'dark' : ''}`}>
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        onOpenIsoModal={() => setIsIsoModalOpen(true)}
      />

      <div className={`main-wrapper ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Topbar onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)} />

        <main className="page-content">
          {renderCurrentRoute()}
        </main>
      </div>

      {/* Global Toast */}
      {state.toast && (
        <Toast
          message={state.toast.message}
          type={state.toast.type}
          onClose={() => dispatch({ type: 'HIDE_TOAST' })}
        />
      )}

      {/* ISO Certificate Modal */}
      {isIsoModalOpen && (
        <IsoCertificateModal
          isOpen={isIsoModalOpen}
          onClose={() => setIsIsoModalOpen(false)}
        />
      )}
    </div>
  );
}
