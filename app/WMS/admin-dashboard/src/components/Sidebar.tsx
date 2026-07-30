import {
  LayoutDashboard,
  Truck,
  PackageCheck,
  MapPinned,
  ShieldCheck,
  Bell,
  FileText,
  Settings,
  ClipboardCheck,
  type LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  "KPI Dashboard": LayoutDashboard,
  Receiving: Truck,
  "Put-away & Slotting": PackageCheck,
  "Picking & Packing": ClipboardCheck,
  "Location Management": MapPinned,
  Dispatch: Truck,
  "Quality & Compliance": ShieldCheck,
  Alerts: Bell,
  Reports: FileText,
  Settings: Settings,
};

const navSections = [
  {
    title: "Dashboard",
    items: ["KPI Dashboard"],
  },
  {
    title: "Inbound",
    items: ["Receiving", "Put-away & Slotting"],
  },
  {
    title: "Operations",
    items: ["Picking & Packing", "Location Management", "Dispatch"],
  },
  {
    title: "Compliance",
    items: ["Quality & Compliance", "Alerts"],
  },
  {
    title: "General",
    items: ["Reports", "Settings"],
  },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">W</div>
        <span>WMS Control Center</span>
      </div>

      <nav className="sidebar-nav">
        {navSections.map((section) => (
            <div className="sidebar-section" key={section.title}>
                <p className="sidebar-section-title">{section.title}</p>
                
            {section.items.map((item) => (
                <button
                key={item}
                className={`sidebar-item ${item === "KPI Dashboard" ? "active" : ""}`}
                type="button"
                >
                {(() => {
                const Icon = iconMap[item];
                return <Icon size={18} strokeWidth={2} />;
                })()}
                <span>{item}</span>
                </button>
                ))}
            </div>
        ))}
     </nav>

      <div className="sidebar-certification">
        <strong>ISO 9001 Certified</strong>
        <p>Warehouse operations follow quality and audit standards.</p>
        <button type="button">View Certificate</button>
      </div>
    </aside>
  );
}

export default Sidebar;