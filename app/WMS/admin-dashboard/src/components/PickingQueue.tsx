import { pickingQueue } from "../data/mockData";

function PickingQueue() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Picking Queue</h2>
          <p>Active pick waves and picker workload</p>
        </div>
        <button type="button">View All</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Wave ID</th>
            <th>Picker</th>
            <th>Zone</th>
            <th>Status</th>
            <th>Pending</th>
            <th>SLA</th>
          </tr>
        </thead>
        <tbody>
          {pickingQueue.map((row) => (
            <tr key={row.waveId}>
              <td>{row.waveId}</td>
              <td>{row.picker}</td>
              <td>{row.zone}</td>
              <td>
                <span className={`status-pill ${row.status.toLowerCase().replace(" ", "-")}`}>
                  {row.status}
                </span>
              </td>
              <td>{row.pendingItems}</td>
              <td>{row.sla}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default PickingQueue;