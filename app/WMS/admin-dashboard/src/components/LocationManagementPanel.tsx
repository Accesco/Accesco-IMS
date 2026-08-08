import { locationInventory } from "../data/mockData";

function LocationManagementPanel() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Location Management</h2>
          <p>Bin-level stock accuracy and physical count status</p>
        </div>
        <button type="button">Start Cycle Count</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Zone</th>
            <th>Bin</th>
            <th>System Qty</th>
            <th>Physical Qty</th>
            <th>Status</th>
          </tr>
        </thead>

        <tbody>
          {locationInventory.map((row) => (
            <tr key={`${row.sku}-${row.bin}`}>
              <td>{row.sku}</td>
              <td>{row.zone}</td>
              <td>{row.bin}</td>
              <td>{row.systemQty}</td>
              <td>{row.physicalQty}</td>
              <td>
                <span className={`status-pill ${row.status.toLowerCase()}`}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default LocationManagementPanel;