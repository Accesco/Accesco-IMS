import { systemHealth } from "../data/mockData";

function SystemHealth() {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>System Health</h2>
          <p>Warehouse service monitoring</p>
        </div>
      </div>

      <div className="health-list">
        {systemHealth.map((service) => (
          <div className="health-item" key={service.service}>
            <div>
              <strong>{service.service}</strong>
              <span>{service.uptime}</span>
            </div>

            <span className={`health-status ${service.status.toLowerCase()}`}>
              {service.status}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default SystemHealth;