import { reportsSummary } from "../data/mockData";

function ReportsPanel() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Reports</h2>
          <p>Warehouse performance reports and operational review documents</p>
        </div>
        <button type="button">Generate Report</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Report Name</th>
            <th>Category</th>
            <th>Frequency</th>
            <th>Owner</th>
            <th>Status</th>
          </tr>
        </thead>

        <tbody>
          {reportsSummary.map((report) => (
            <tr key={report.reportName}>
              <td>{report.reportName}</td>
              <td>{report.category}</td>
              <td>{report.frequency}</td>
              <td>{report.owner}</td>
              <td>
                <span className={`status-pill ${report.status.toLowerCase()}`}>
                  {report.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default ReportsPanel;