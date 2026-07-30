import { warehouseStatus } from "../data/mockData";

function WarehouseStatus() {
  return (
    <section className="warehouse-status-card">
      <div>
        <h2>Live Warehouse Status</h2>
        <p>Updated 2 min ago</p>
      </div>

      <div className="warehouse-status-grid">
        {warehouseStatus.map((item) => (
          <div className="warehouse-status-item" key={item.area}>
            <span className={`status-dot ${item.tone}`} />
            <div>
              <strong>{item.area}</strong>
              <p>{item.state}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default WarehouseStatus;