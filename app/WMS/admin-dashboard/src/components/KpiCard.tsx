type KpiCardProps = {
  title: string;
  value: string | number;
  change: string;
  tone: "green" | "blue" | "orange" | "red" | "purple" | "teal";
};

function KpiCard({ title, value, change, tone }: KpiCardProps) {
  return (
    <article className="kpi-card">
      <div className={`kpi-icon ${tone}`} />

      <div>
        <h3>{value}</h3>
        <p>{title}</p>
        <span className={`kpi-change ${tone}`}>{change}</span>
      </div>
    </article>
  );
}

export default KpiCard;