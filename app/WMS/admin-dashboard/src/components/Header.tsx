import { useState } from "react";
import { notifications } from "../data/mockData";
type HeaderProps = {
  theme: "light" | "dark";
  onToggleTheme: () => void;
};



function Header({ theme, onToggleTheme }: HeaderProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  return (
    <header className="top-header">
      <div className="search-box">
        <span>⌕</span>
        <input
          type="text"
          placeholder="Search SKU, PO, Bin, Batch, Pick Wave..."
        />
      </div>

      <div className="header-filters">
        <select>
          <option>All Warehouses</option>
          <option>Bangalore WH03</option>
          <option>Hyderabad WH04</option>
          <option>Pune WH05</option>
        </select>

        <select>
          <option>All Zones</option>
          <option>Receiving</option>
          <option>Picking</option>
          <option>Packing</option>
          <option>Dispatch</option>
        </select>

        <select>
          <option>All Statuses</option>
          <option>Operational</option>
          <option>Delayed</option>
          <option>Attention Needed</option>
        </select>

        <div className="notification-wrapper">
          <button
            className="icon-button notification-button"
            type="button"
            onClick={() => setShowNotifications((current) => !current)}
          >
            🔔
            <span className="notification-badge">{notifications.length}</span>
          </button>

          {showNotifications && (
            <div className="notification-menu">
              <div className="notification-menu-header">
                <strong>Notifications</strong>
                <span>{notifications.length} new</span>
              </div>
              {notifications.map((item) => (
                <div className="notification-item" key={item.title}>
                  <span className={`status-dot ${item.tone}`} />
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                    <small>{item.time}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        

        <button className="icon-button" type="button" onClick={onToggleTheme}>
          {theme === "dark" ?  "☀" : "☾"} {/*Make this lucid icons*/}
        </button>

        <div className="profile-chip">A</div>
      </div>
    </header>
  );
}

export default Header;
