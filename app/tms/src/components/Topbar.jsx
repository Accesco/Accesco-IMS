import React, { useState, useEffect, useRef } from 'react';
import { useTMS } from '../context/TMSContext';
import {
  Search,
  Bell,
  Sun,
  Moon,
  Settings,
  ChevronDown,
  User,
  SlidersHorizontal,
  LogOut,
  MapPin,
  Building2,
  Package,
  Truck,
  FileText
} from 'lucide-react';
import styles from '../styles/topbar.module.css';

export default function Topbar({ onToggleMobileSidebar }) {
  const { state, dispatch, showToast } = useTMS();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const searchRef = useRef(null);

  const unreadAlerts = state.alerts.filter((a) => a.readStatus === 'Unread');

  // Handle keyboard shortcut Command+K or Ctrl+K for search
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Filter global search results
  const getSearchResults = () => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    const results = [];

    // Search ERP Orders
    state.orders.forEach((o) => {
      if (
        o.id.toLowerCase().includes(q) ||
        o.erpRef.toLowerCase().includes(q) ||
        o.destinationName.toLowerCase().includes(q)
      ) {
        results.push({
          type: 'Order',
          title: `${o.erpRef} (${o.id})`,
          sub: `${o.originName} ➔ ${o.destinationName}`,
          path: '/erp-orders',
          icon: Package,
        });
      }
    });

    // Search Shipments
    state.shipments.forEach((s) => {
      if (
        s.id.toLowerCase().includes(q) ||
        s.carrierName?.toLowerCase().includes(q) ||
        s.destinationName?.toLowerCase().includes(q)
      ) {
        results.push({
          type: 'Shipment',
          title: s.id,
          sub: `${s.carrierName || 'Unassigned'} - ${s.shipmentStatus}`,
          path: '/shipments',
          icon: Truck,
        });
      }
    });

    // Search Carriers
    state.carriers.forEach((c) => {
      if (
        c.name.toLowerCase().includes(q) ||
        c.scac.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q)
      ) {
        results.push({
          type: 'Carrier',
          title: `${c.name} (${c.scac})`,
          sub: `Status: ${c.status} | Tier: ${c.performanceTier}`,
          path: '/carriers',
          icon: Building2,
        });
      }
    });

    // Search Invoices
    state.invoices.forEach((inv) => {
      if (inv.id.toLowerCase().includes(q) || inv.shipmentId.toLowerCase().includes(q)) {
        results.push({
          type: 'Invoice',
          title: inv.id,
          sub: `Shipment ${inv.shipmentId} - SAR ${inv.submittedTotalSAR}`,
          path: '/freight-audit',
          icon: FileText,
        });
      }
    });

    return results.slice(0, 8);
  };

  const searchResults = getSearchResults();

  const handleSelectResult = (path) => {
    dispatch({ type: 'SET_ROUTE', payload: path });
    setIsSearchOpen(false);
    setSearchQuery('');
  };

  const toggleDarkMode = () => {
    const newDarkMode = !state.settings.darkMode;
    dispatch({
      type: 'UPDATE_SETTINGS',
      payload: { darkMode: newDarkMode },
    });
    showToast(`Switched to ${newDarkMode ? 'Dark' : 'Light'} mode`, 'info');
  };

  const handleOriginChange = (e) => {
    dispatch({
      type: 'SET_FILTERS',
      payload: { originComplex: e.target.value },
    });
  };

  const handleVerticalChange = (e) => {
    dispatch({
      type: 'SET_FILTERS',
      payload: { businessVertical: e.target.value },
    });
  };

  return (
    <header className={styles.topbar}>
      <div className={styles.leftSection}>
        {/* Mobile menu trigger */}
        <button
          className={styles.mobileMenuBtn}
          onClick={onToggleMobileSidebar}
          aria-label="Open Navigation Menu"
        >
          <SlidersHorizontal size={18} />
        </button>

        {/* Global Search Input */}
        <div className={styles.searchWrapper}>
          <Search size={16} className={styles.searchIcon} />
          <input
            ref={searchRef}
            type="text"
            className={styles.searchInput}
            placeholder="Search orders, shipments, carriers, lanes..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsSearchOpen(true);
            }}
            onFocus={() => setIsSearchOpen(true)}
          />
          <span className={styles.searchKbd}>⌘K</span>

          {/* Search Dropdown */}
          {isSearchOpen && searchResults.length > 0 && (
            <div className={styles.searchDropdown}>
              <div className={styles.dropdownHeader}>Search Results</div>
              {searchResults.map((res, idx) => {
                const ResIcon = res.icon;
                return (
                  <div
                    key={idx}
                    className={styles.searchResultItem}
                    onClick={() => handleSelectResult(res.path)}
                  >
                    <div className={styles.resIconBox}>
                      <ResIcon size={14} />
                    </div>
                    <div className={styles.resInfo}>
                      <div className={styles.resTitle}>
                        {res.title}{' '}
                        <span className={styles.resTypeBadge}>{res.type}</span>
                      </div>
                      <div className={styles.resSub}>{res.sub}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className={styles.rightSection}>
        {/* Origin Complex Dropdown */}
        <div className={styles.selectGroup}>
          <MapPin size={14} className={styles.selectIcon} />
          <select
            className={styles.topSelect}
            value={state.filters.originComplex}
            onChange={handleOriginChange}
          >
            <option value="All Origin Complexes">All Origin Complexes</option>
            <option value="BGL-CENTRAL">Bengaluru Central Hub</option>
            <option value="BGL-NORTH">Bengaluru North Hub</option>
            <option value="HYD-HUB">Hyderabad Hub</option>
            <option value="CHN-HUB">Chennai Hub</option>
            <option value="MUM-HUB">Mumbai Hub</option>
          </select>
        </div>

        {/* Business Vertical Dropdown */}
        <div className={styles.selectGroup}>
          <Building2 size={14} className={styles.selectIcon} />
          <select
            className={styles.topSelect}
            value={state.filters.businessVertical}
            onChange={handleVerticalChange}
          >
            <option value="All Verticals">All Verticals</option>
            <option value="Retail">Retail</option>
            <option value="E-commerce">E-commerce</option>
            <option value="Grocery">Grocery</option>
            <option value="Lifestyle">Lifestyle</option>
            <option value="Manufacturing">Manufacturing</option>
          </select>
        </div>

        {/* Notifications */}
        <div className={styles.iconPopWrapper}>
          <button
            className={styles.iconBtn}
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            title="Notifications & Alerts"
            aria-label="Open Notifications"
          >
            <Bell size={18} />
            {unreadAlerts.length > 0 && (
              <span className={styles.notifBadge}>{unreadAlerts.length}</span>
            )}
          </button>

          {isNotifOpen && (
            <div className={styles.notifDropdown}>
              <div className={styles.notifHeader}>
                <span>Notifications ({unreadAlerts.length})</span>
                <button
                  className={styles.markReadBtn}
                  onClick={() => dispatch({ type: 'MARK_ALL_ALERTS_READ' })}
                >
                  Mark all read
                </button>
              </div>
              <div className={styles.notifList}>
                {unreadAlerts.length === 0 ? (
                  <div className={styles.emptyNotif}>No unread alerts</div>
                ) : (
                  unreadAlerts.slice(0, 5).map((a) => (
                    <div
                      key={a.id}
                      className={styles.notifItem}
                      onClick={() => {
                        dispatch({ type: 'SET_ROUTE', payload: '/alerts' });
                        setIsNotifOpen(false);
                      }}
                    >
                      <div className={styles.notifMsg}>{a.message}</div>
                      <div className={styles.notifTime}>{a.createdTime}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Dark Mode Toggle */}
        <button
          className={styles.iconBtn}
          onClick={toggleDarkMode}
          title={state.settings.darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label="Toggle Dark Mode"
        >
          {state.settings.darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* Settings Route Button */}
        <button
          className={styles.iconBtn}
          onClick={() => dispatch({ type: 'SET_ROUTE', payload: '/settings' })}
          title="TMS Settings"
          aria-label="Open Settings"
        >
          <Settings size={18} />
        </button>

        {/* User Profile Avatar */}
        <div className={styles.userMenuWrapper}>
          <button
            className={styles.userAvatarBtn}
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          >
            <div className={styles.avatarCircle}>AM</div>
            <span className={styles.userName}>Adithi M</span>
            <ChevronDown size={14} />
          </button>

          {isUserMenuOpen && (
            <div className={styles.userDropdown}>
              <div className={styles.userInfoBox}>
                <div className={styles.userFullName}>Adithi M</div>
                <div className={styles.userEmail}>adithiganti07@gmail.com</div>
                <div className={styles.userRole}>Transportation Director</div>
              </div>
              <hr className={styles.menuDivider} />
              <button
                className={styles.dropdownOption}
                onClick={() => {
                  dispatch({ type: 'SET_ROUTE', payload: '/settings' });
                  setIsUserMenuOpen(false);
                }}
              >
                <User size={14} />
                My Profile
              </button>
              <button
                className={styles.dropdownOption}
                onClick={() => {
                  dispatch({ type: 'SET_ROUTE', payload: '/settings' });
                  setIsUserMenuOpen(false);
                }}
              >
                <Settings size={14} />
                Preferences
              </button>
              <hr className={styles.menuDivider} />
              <button
                className={styles.dropdownOption}
                onClick={() => {
                  showToast('Signed out of Accesco Living TMS session', 'info');
                  setIsUserMenuOpen(false);
                }}
              >
                <LogOut size={14} />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
