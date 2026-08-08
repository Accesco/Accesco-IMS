import React, { useState } from 'react';
import { useTMS } from '../context/TMSContext';
import FilterBar from '../components/FilterBar';
import KPICard from '../components/KPICard';
import KpiDetailModal from '../components/KpiDetailModal';
import {
  PackageOpen,
  Truck,
  Boxes,
  Gauge,
  Handshake,
  Clock,
  TriangleAlert,
  BadgeCheck,
  ArrowUpRight,
  TrendingUp,
  AlertCircle,
  Eye,
  Layers,
  BarChart2
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend
} from 'recharts';
import styles from '../styles/dashboard.module.css';

export default function ControlCenter() {
  const { state, dispatch } = useTMS();
  const [selectedKpi, setSelectedKpi] = useState(null);
  const [volumeTimeframe, setVolumeTimeframe] = useState('Monthly');

  // Filtered metrics calculations
  const unallocatedOrdersCount = state.orders.filter(
    (o) => o.allocationStatus === 'Unallocated'
  ).length;

  const activeShipmentsCount = state.shipments.filter((s) =>
    ['In Transit', 'Tendering', 'Carrier Assigned', 'Planned'].includes(s.shipmentStatus)
  ).length;

  const kpis = [
    {
      id: 'kpi-1',
      title: 'Unallocated Orders',
      value: unallocatedOrdersCount || '134',
      description: 'Orders received from ERP but not yet assigned to transport runs',
      changeText: '-12% vs last week',
      isPositive: true,
      icon: PackageOpen,
      accentColor: '#f59e0b',
      sparklineData: [160, 152, 145, 140, 138, 135, 134],
      prevValue: '152',
      definition: 'Measures total order line-items currently sitting in unallocated status awaiting continuous consolidation or dedicated dispatch assignment.',
      relatedSummary: 'Orders awaiting consolidation from Bengaluru Central, Hyderabad, and Chennai hubs.',
      targetRoute: '/erp-orders',
    },
    {
      id: 'kpi-2',
      title: 'Active Shipments',
      value: activeShipmentsCount || '1,957',
      description: 'Shipments currently allocated, tendered, assigned or in transit',
      changeText: '+8.4% vs last week',
      isPositive: true,
      icon: Truck,
      accentColor: '#8b5cf6',
      sparklineData: [1750, 1800, 1850, 1890, 1910, 1940, 1957],
      prevValue: '1,805',
      definition: 'Total active transport runs being executed across FTL, LTL, Milk-run, Dedicated, and Cold Chain modes.',
      relatedSummary: '142 active in South Zone, 85 in West Zone, 42 in North Zone.',
      targetRoute: '/shipments',
    },
    {
      id: 'kpi-3',
      title: 'Consolidation Rate',
      value: '82.6%',
      description: 'Percentage of eligible orders combined into consolidated runs',
      changeText: '+3.1% vs target',
      isPositive: true,
      icon: Boxes,
      accentColor: '#2563eb',
      sparklineData: [76, 78, 79, 81, 80, 82, 82.6],
      prevValue: '79.5%',
      definition: 'Calculates the volumetric and weight efficiency ratio of orders merged into higher-density FTL or Milk-run schedules versus solo LTL.',
      relatedSummary: 'High consolidation efficiency in South and West logistics corridors.',
      targetRoute: '/consolidation',
    },
    {
      id: 'kpi-4',
      title: 'Average Asset Utilisation',
      value: '91.4%',
      description: 'Combined vehicle weight and cubic-volume utilisation',
      changeText: '+1.8% vs last week',
      isPositive: true,
      icon: Gauge,
      accentColor: '#06b6d4',
      sparklineData: [85, 87, 88, 90, 89, 91, 91.4],
      prevValue: '89.6%',
      definition: 'Measures the mathematical average of weight payload (max 18,000 kg) and volumetric cube (max 60.0 CBM) filled across assigned vehicles.',
      relatedSummary: 'Container and Heavy Truck fleets operating above 90% capacity margin.',
      targetRoute: '/capacity',
    },
    {
      id: 'kpi-5',
      title: 'Tender Acceptance',
      value: '88.2%',
      description: 'Carrier tenders accepted within the 60-minute response window',
      changeText: '+2.5% vs target',
      isPositive: true,
      icon: Handshake,
      accentColor: '#16a34a',
      sparklineData: [82, 84, 85, 86, 87, 88, 88.2],
      prevValue: '85.7%',
      definition: 'Percentage of sequential contract tender invitations accepted by Tier 1 and Tier 2 carriers before the 60-minute waterfall timer expires.',
      relatedSummary: 'Accesco Express Logistics and Safexpress leading acceptance rates.',
      targetRoute: '/tenders',
    },
    {
      id: 'kpi-6',
      title: 'On-Time Compliance',
      value: '96.4%',
      description: 'Shipments completed within the required delivery window',
      changeText: '+0.8% vs SLA',
      isPositive: true,
      icon: Clock,
      accentColor: '#14b8a6',
      sparklineData: [94, 95, 95.5, 96, 96.1, 96.3, 96.4],
      prevValue: '95.6%',
      definition: 'Measures carrier SLA adherence by comparing actual delivery timestamps against strict ERP required delivery windows.',
      relatedSummary: 'Zero critical SLA failures in South Zone over past 48 hours.',
      targetRoute: '/tracking',
    },
    {
      id: 'kpi-7',
      title: 'ETA Exceptions',
      value: state.alerts.length || '29',
      description: 'Shipments with route, ETA drift, temperature or geofence exceptions',
      changeText: '-5 cases vs yesterday',
      isPositive: true,
      icon: TriangleAlert,
      accentColor: '#ef4444',
      sparklineData: [45, 40, 38, 35, 32, 30, 29],
      prevValue: '34',
      definition: 'Active shipments experiencing live telemetry exceptions including ETA drift >30 mins, geofence breaches, or reefer temperature deviations.',
      relatedSummary: '4 high-severity alerts currently monitored by Route Control.',
      targetRoute: '/alerts',
    },
    {
      id: 'kpi-8',
      title: 'Freight Audit Pass Rate',
      value: '98.7%',
      description: 'Carrier invoices passing automated three-way verification',
      changeText: '+1.2% pass rate',
      isPositive: true,
      icon: BadgeCheck,
      accentColor: '#f59e0b',
      sparklineData: [95, 96, 97, 97.5, 98, 98.4, 98.7],
      prevValue: '97.5%',
      definition: 'Percentage of carrier freight invoices matching contracted tariff linehaul, fuel surcharges, and execution records without variance.',
      relatedSummary: 'Automated ledger release active for 98.7% verified invoices.',
      targetRoute: '/freight-audit',
    },
  ];

  // Mock chart data
  const volumeTrendData = [
    { name: 'Jan', Total: 1200, Consolidated: 980, Dedicated: 220 },
    { name: 'Feb', Total: 1350, Consolidated: 1100, Dedicated: 250 },
    { name: 'Mar', Total: 1500, Consolidated: 1240, Dedicated: 260 },
    { name: 'Apr', Total: 1420, Consolidated: 1180, Dedicated: 240 },
    { name: 'May', Total: 1680, Consolidated: 1390, Dedicated: 290 },
    { name: 'Jun', Total: 1820, Consolidated: 1520, Dedicated: 300 },
    { name: 'Jul', Total: 1957, Consolidated: 1616, Dedicated: 341 },
  ];

  const capacityUtilData = [
    { name: 'Under 50%', value: 8, color: '#6b7280' },
    { name: '50% to 75%', value: 22, color: '#3b82f6' },
    { name: '75% to 90%', value: 45, color: '#06b6d4' },
    { name: 'Above 90%', value: 25, color: '#16a34a' },
  ];

  const procurementFunnelData = [
    { stage: 'Contracts Identified', count: 180 },
    { stage: 'Tenders Dispatched', count: 165 },
    { stage: 'Accepted', count: 145 },
    { stage: 'Rejected', count: 12 },
    { stage: 'Timed Out', count: 8 },
    { stage: 'Spot Auction', count: 5 },
    { stage: 'Human Dispatch', count: 2 },
  ];

  const carrierPerformanceData = [
    { name: 'Accesco Exp', OnTime: 98, TenderAcc: 94, CostScore: 92 },
    { name: 'Safexpress', OnTime: 97, TenderAcc: 92, CostScore: 90 },
    { name: 'Rivigo Cold', OnTime: 96, TenderAcc: 91, CostScore: 88 },
    { name: 'VRL Freight', OnTime: 94, TenderAcc: 89, CostScore: 95 },
    { name: 'GATI KWE', OnTime: 91, TenderAcc: 84, CostScore: 86 },
  ];

  const shipmentStatusData = [
    { name: 'Unallocated', value: 12, color: '#f59e0b' },
    { name: 'Consolidating', value: 18, color: '#8b5cf6' },
    { name: 'Tendering', value: 15, color: '#3b82f6' },
    { name: 'Carrier Assigned', value: 25, color: '#10b981' },
    { name: 'In Transit', value: 48, color: '#2563eb' },
    { name: 'Delivered', value: 35, color: '#16a34a' },
    { name: 'Exception', value: 4, color: '#ef4444' },
  ];

  return (
    <div className="animate-fade-in">
      {/* Control Center Filter Bar */}
      <FilterBar />

      {/* KPI Cards 8-Grid */}
      <div className={styles.kpiGrid}>
        {kpis.map((kpi) => (
          <KPICard
            key={kpi.id}
            title={kpi.title}
            value={kpi.value}
            description={kpi.description}
            changeText={kpi.changeText}
            isPositive={kpi.isPositive}
            icon={kpi.icon}
            accentColor={kpi.accentColor}
            sparklineData={kpi.sparklineData}
            onClick={() => setSelectedKpi(kpi)}
          />
        ))}
      </div>

      {/* Primary Analytics Charts Row */}
      <div className={styles.chartsGrid}>
        {/* A. Shipment Volume Trend Area Chart */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <div className={styles.chartTitleGroup}>
              <div className="card-title">
                <BarChart2 size={18} color="var(--primary-blue)" />
                Shipment Volume Trend
              </div>
              <div className="card-subtitle">
                Historical order volume, consolidated runs & dedicated loads
              </div>
            </div>

            <div className={styles.tabGroup}>
              {['Daily', 'Weekly', 'Monthly', 'Yearly'].map((t) => (
                <button
                  key={t}
                  className={`${styles.tabBtn} ${
                    volumeTimeframe === t ? styles.tabBtnActive : ''
                  }`}
                  onClick={() => setVolumeTimeframe(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={volumeTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorConsolidated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="name" stroke="var(--secondary-text)" fontSize={11} />
                <YAxis stroke="var(--secondary-text)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card-bg)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Area type="monotone" dataKey="Total" stroke="#2563eb" fillOpacity={1} fill="url(#colorTotal)" />
                <Area type="monotone" dataKey="Consolidated" stroke="#16a34a" fillOpacity={1} fill="url(#colorConsolidated)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* B. Capacity Utilisation Donut */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <div className={styles.chartTitleGroup}>
              <div className="card-title">
                <Gauge size={18} color="#06b6d4" />
                Capacity Utilisation
              </div>
              <div className="card-subtitle">Weight & volume load density distribution</div>
            </div>
          </div>

          <div className={styles.chartContainer} style={{ position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={capacityUtilData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {capacityUtilData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card-bg)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '20px', fontWeight: '800' }}>91.4%</div>
              <div style={{ fontSize: '10px', color: 'var(--secondary-text)' }}>Avg Utilisation</div>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Charts Row: Procurement Funnel & Carrier Performance & Recent Exceptions */}
      <div className={styles.chartsGrid}>
        {/* C. Procurement Waterfall Funnel */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <div className={styles.chartTitleGroup}>
              <div className="card-title">
                <Handshake size={18} color="#16a34a" />
                Procurement Funnel & Waterfall
              </div>
              <div className="card-subtitle">From contract identification to acceptance or spot auction</div>
            </div>
          </div>

          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={procurementFunnelData} layout="vertical" margin={{ top: 0, right: 20, left: 40, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis type="number" stroke="var(--secondary-text)" fontSize={11} />
                <YAxis dataKey="stage" type="category" stroke="var(--secondary-text)" fontSize={11} width={110} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--card-bg)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" fill="#2563eb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Exceptions Sidebar Panel */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <div className={styles.chartTitleGroup}>
              <div className="card-title">
                <TriangleAlert size={18} color="#ef4444" />
                Recent Exceptions
              </div>
              <div className="card-subtitle">Live telemetry, ETA drift & tariff alerts</div>
            </div>
            <button
              className="tms-button tms-btn-secondary tms-btn-sm"
              onClick={() => dispatch({ type: 'SET_ROUTE', payload: '/alerts' })}
            >
              View All
            </button>
          </div>

          <div className={styles.exceptionList}>
            {state.alerts.slice(0, 4).map((alt) => (
              <div key={alt.id} className={styles.exceptionItem}>
                <div className={styles.exceptionInfo}>
                  <div className={styles.exceptionTitle}>{alt.type}</div>
                  <div className={styles.exceptionSub}>{alt.message.substring(0, 65)}...</div>
                </div>
                <button
                  className="tms-button tms-btn-secondary tms-btn-sm"
                  onClick={() => dispatch({ type: 'SET_ROUTE', payload: '/alerts' })}
                >
                  <Eye size={12} /> Inspect
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Detail Modal */}
      {selectedKpi && (
        <KpiDetailModal
          kpiData={selectedKpi}
          isOpen={!!selectedKpi}
          onClose={() => setSelectedKpi(null)}
        />
      )}
    </div>
  );
}
