import { dispatchQueue } from "../data/mockData";

function DispatchStaging() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Dispatch Staging</h2>
          <p>Packed orders waiting for rider handoff</p>
        </div>
        <button type="button">Export</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Zone</th>
            <th>Packed Status</th>
            <th>Handoff</th>
            <th>Carrier</th>
          </tr>
        </thead>

        <tbody>
          {dispatchQueue.map((row) => (
            <tr key={row.orderId}>
              <td>{row.orderId}</td>
              <td>{row.zone}</td>
              <td>
                <span className={`status-pill ${row.packedStatus.toLowerCase().replace(" ", "-")}`}>
                  {row.packedStatus}
                </span>
              </td>
              <td>{row.handoffStatus}</td>
              <td>{row.carrier}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default DispatchStaging;