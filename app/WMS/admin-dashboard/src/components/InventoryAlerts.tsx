import { inventoryAlerts } from "../data/mockData";

function InventoryAlerts() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Inventory Alerts</h2>
          <p>Stock exceptions requiring warehouse action</p>
        </div>
        <button type="button">Review</button>
      </div>

      <div className="alert-list">
        {inventoryAlerts.map((alert) => (
          <div className="alert-item" key={`${alert.type}-${alert.item}`}>
            <div>
              <strong>{alert.type}</strong>
              <p>{alert.item}</p>
              <span>{alert.location}</span>
            </div>

            <span className={`severity-pill ${alert.severity.toLowerCase()}`}>
              {alert.severity}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default InventoryAlerts;