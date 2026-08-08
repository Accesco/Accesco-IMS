import { putawayTasks } from "../data/mockData"

function PutawaySlottingPanel(){
    return(
        <section className="panel">
            <div className="panel-header">
                <div>
                    <h2>Put-away & Slotting</h2>
                    <p>Suggested bin placement after receiving and quality check.</p>
                </div>
                <button type="button">Assign Task</button>
            </div>

            <table className="data-table">
                <thead>
                    <tr>
                        <th>Task ID</th>
                        <th>SKU</th>
                        <th>Category</th>
                        <th>Suggested</th>
                        <th>Priority</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                    {putawayTasks.map((task) => (
                        <tr key = {task.taskId}>
                            <td>{task.taskId}</td>
                            <td>{task.sku}</td>
                            <td>{task.category}</td>
                            <td>{task.suggestedBin}</td>
                            <td>
                                <span className={`priority-pill ${task.priority.toLowerCase()}`}>
                                    {task.priority}
                                </span>
                            </td>

                            <td>
                                <span className= {`status-pill ${task.status.toLowerCase().replace(" ","-")}`}>
                                    {task.status}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </section>
    );
}

export default PutawaySlottingPanel;