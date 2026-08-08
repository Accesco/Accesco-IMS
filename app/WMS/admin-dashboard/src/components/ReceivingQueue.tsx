import { receivingQueue } from "../data/mockData";

function ReceivingPanel(){
    return (
        <section className="panel">
            <div className="panel-header">
                <div>
                    <h2>Receiving</h2>
                    <p>Inbound purchase order and dock-level receiving status</p>
                </div>
                <button type="button">Receive Shipment</button>
            </div>

            <table className="data-table">
                <thead>
                    <tr>
                        <th>PO Number</th>
                        <th>Supplier</th>
                        <th>Dock</th>
                        <th>Expected</th>
                        <th>Received</th>
                        <th>QC Status</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                    {receivingQueue.map((row) => (
                        <tr key = {row.poNumber}>
                            <td>{row.supplier}</td>
                            <td>{row.dock}</td>
                            <td>{row.expectedUnits}</td>
                            <td>{row.receivedUnits}</td>
                            <td>
                                <span className={`status-pill ${row.qcStatus.toLowerCase().replace(" ","-")}`}>
                                    {row.qcStatus}
                                </span>
                            </td>
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
    )
}


export default ReceivingPanel;