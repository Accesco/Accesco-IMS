import "./App.css";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import { kpiCards } from "./data/mockData";
import KpiCard from "./components/KpiCard";
import PickingQueue from "./components/PickingQueue";
import InventoryAlerts from "./components/InventoryAlerts";
import SystemHealth from "./components/SystemHealth";
import DispatchStaging from "./components/DispatchStaging";
import WarehouseStatus from "./components/Warehouse";

function App() {
  return (
    <div className="app-shell">
      <Sidebar />

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

          <WarehouseStatus />

          <div className="kpi-grid">
            {kpiCards.map((card) => (
              <KpiCard key={card.title} {...card} />
            ))}
          </div>

          <div className="dashboard-grid">
            <PickingQueue />
            <DispatchStaging />

            <div className="side-panels">
              <InventoryAlerts />
              <SystemHealth />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;