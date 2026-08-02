import "./App.css";
import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import { kpiCards } from "./data/mockData";
import KpiCard from "./components/KpiCard";
import PickingQueue from "./components/PickingQueue";
import InventoryAlerts from "./components/InventoryAlerts";
import SystemHealth from "./components/SystemHealth";
import DispatchStaging from "./components/DispatchStaging";
import WarehouseStatus from "./components/Warehouse";
import ReceivingPanel from "./components/ReceivingQueue";
import PutawaySlottingPanel from "./components/PutawaySlottingPanel";
import LocationManagementPanel from "./components/LocationManagementPanel";
import QualityCompliancePanel from "./components/QualityCompliancePanel";
import ReportsPanel from "./components/ReportPanel";



function App() {
  const [activeSection, setActiveSection] = useState("KPI Dashboard");
  
  return (
    <div className="app-shell">
      <Sidebar 
        activeSection={activeSection}
        onSectionChange={setActiveSection}
      />
      <main className="main-content">
        <Header />

        <section className="dashboard-content">
          <div className="page-header-row">
            <div className="page-title">
              <h1>WMS Control Center</h1>
              <p>Warehouse operations overview • Live simulation</p>
            </div>

            <div className="quick-actions">
              <button type="button">Receive Shipment</button>
              <button type="button">Create Pick Wave</button>
              <button type="button">Dispatch Batch</button>
              <button type="button">Add Warehouse</button>
            </div>
          </div>

          {activeSection === "KPI Dashboard" && (
            <>
              <WarehouseStatus />

              <div className="kpi-grid">
                {kpiCards.map((card) => (
                  <KpiCard key={card.title} {...card} />
                ))}
              </div>

              <div className="dashboard-grid">
                <div className="side-panels">
                  <InventoryAlerts />
                  <SystemHealth />
                </div>
              </div>
            </>
          )}


          {activeSection === "Receiving" && (
            <div className="dashboard-grid">
              <ReceivingPanel/>
            </div>
          )}

          {activeSection === "Put-away & Slotting" && (
            <div className="dashboard-grid">
              <PutawaySlottingPanel/>
            </div>
          )} 


          {activeSection === "Picking & Packing" && (
            <div className="dashboard-grid">
              <PickingQueue />
            </div>
          )}

          {activeSection === "Location Management" && (
            <div className="dashboard-grid">
              <LocationManagementPanel/>
            </div>
          )}

          {activeSection === "Dispatch" && (
            <div className="dashboard-grid">
              <DispatchStaging />
            </div>
          )}

          {activeSection === "Quality & Compliance" && (
            <div className="dashboard-grid">
              <QualityCompliancePanel/>
            </div>
          )}

          {activeSection === "Reports" && (
            <div className="dashboard-grid">
              <ReportsPanel />
            </div>
          )}



          {activeSection === "Alerts" && (
            <div className="dashboard-grid">
              <InventoryAlerts />
            </div>
          )}

        </section>
      </main>
    </div>
  );
}

export default App;