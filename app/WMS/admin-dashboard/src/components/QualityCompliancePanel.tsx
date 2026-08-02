import { qualityChecks } from "../data/mockData";

function QualityCompliancePanel() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Quality & Compliance</h2>
          <p>QC holds, expiry risk, damaged stock, and cycle count exceptions</p>
        </div>
        <button type="button">Open CAPA</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Check ID</th>
            <th>Item</th>
            <th>Issue</th>
            <th>Zone</th>
            <th>Status</th>
            <th>Owner</th>
          </tr>
        </thead>

        <tbody>
          {qualityChecks.map((check) => (
            <tr key={check.checkId}>
              <td>{check.checkId}</td>
              <td>{check.item}</td>
              <td>{check.issue}</td>
              <td>{check.zone}</td>
              <td>
                <span className={`status-pill ${check.status.toLowerCase().replace(" ", "-")}`}>
                  {check.status}
                </span>
              </td>
              <td>{check.owner}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default QualityCompliancePanel;