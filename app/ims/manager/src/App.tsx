import { useMemo, useRef, useState } from 'react';

type StockStatus = 'Healthy' | 'Low' | 'Out of Stock' | 'Excess';

type StockItem = {
  icon: string;
  sku: string;
  title: string;
  location: string;
  type: 'DC' | 'DS';
  inventory: number;
  reserved: number;
  available: number;
  value: string;
  status: StockStatus;
};

const stockItems: StockItem[] = [
  { icon: '♟', sku: 'CH-001', title: 'Ergonomic Office Chair', location: 'DC-BLR-01', type: 'DC', inventory: 4820, reserved: 320, available: 4500, value: '₹ 1,03,630', status: 'Healthy' },
  { icon: '▰', sku: 'TB-002', title: 'Conference Table', location: 'DS-KOR-04', type: 'DS', inventory: 120, reserved: 15, available: 105, value: '₹ 2,31,750', status: 'Low' },
  { icon: '⌞', sku: 'LT-003', title: 'LED Desk Lamp', location: 'DS-IND-07', type: 'DS', inventory: 0, reserved: 0, available: 0, value: '₹ 0', status: 'Out of Stock' },
  { icon: '▥', sku: 'FC-004', title: 'Filing Cabinet', location: 'DC-BLR-01', type: 'DC', inventory: 2200, reserved: 150, available: 2050, value: '₹ 1,82,450', status: 'Healthy' },
  { icon: '▣', sku: 'MN-005', title: '24″ Monitor', location: 'DS-KOR-04', type: 'DS', inventory: 300, reserved: 20, available: 280, value: '₹ 1,12,000', status: 'Excess' },
];

type NavIconName = 'dashboard' | 'ledger' | 'discrepancy' | 'writeoff' | 'clock';
type MetricIconName = 'package' | 'building' | 'warning' | 'empty-package';

const navigation: { icon: NavIconName; label: string }[] = [
  { icon: 'dashboard', label: 'Dashboard' },
  { icon: 'ledger', label: 'Stock Ledger' },
  { icon: 'discrepancy', label: 'Discrepancy Queue' },
  { icon: 'writeoff', label: 'Write-off Approvals' },
  { icon: 'clock', label: 'Reservation Overrides' },
];

const locations = [
  { icon: '◎', title: 'All Locations', subtitle: 'All 4 locations' },
  { icon: '◉', title: 'DC-BLR-01', subtitle: 'Distribution Center' },
  { icon: '♙', title: 'DS-KOR-04', subtitle: 'Koramangala' },
  { icon: '◉', title: 'DS-IND-07', subtitle: 'Indiranagar' },
  { icon: '♙', title: 'DS-HSR-02', subtitle: 'HSR Layout' },
];

type SortKey = 'sku' | 'title' | 'location' | 'inventory' | 'reserved' | 'available' | 'value' | 'status';
type ViewName = 'Stock Ledger' | 'Discrepancy Queue' | 'Write-off Approvals' | 'Reservation Overrides';

function ChevronIcon({ direction = 'down' }: { direction?: 'down' | 'left' | 'right' }) {
  const rotation = direction === 'left' ? 'rotate(90 10 10)' : direction === 'right' ? 'rotate(-90 10 10)' : undefined;
  return (
    <svg className="ui-chevron" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M5.25 7.75 10 12.5l4.75-4.75" transform={rotation} />
    </svg>
  );
}

function PageEdgeIcon({ direction }: { direction: 'first' | 'last' }) {
  const isFirst = direction === 'first';
  return (
    <svg className="page-edge-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d={isFirst ? 'M12.5 5.5 8 10l4.5 4.5M5.5 5v10' : 'M7.5 5.5 12 10l-4.5 4.5M14.5 5v10'} />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg className="filter-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M3.5 5h13M6 10h8M8.5 15h3" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="topbar-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 15.1A8.5 8.5 0 0 1 8.9 4a8.5 8.5 0 1 0 11.1 11.1Z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg className="topbar-icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="3.5" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg className="topbar-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Z" />
      <path d="M10 21h4" />
    </svg>
  );
}

function NavIcon({ name }: { name: NavIconName }) {
  if (name === 'dashboard') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></svg>;
  }
  if (name === 'ledger') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3.5" width="14" height="17" rx="2" /><path d="M8.5 8h7M8.5 12h7M8.5 16h5" /></svg>;
  }
  if (name === 'clock') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3.5 2" /></svg>;
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="7" cy="7" r="2.5" /><circle cx="17" cy="7" r="2.5" /><circle cx="7" cy="17" r="2.5" /><circle cx="17" cy="17" r="2.5" />
      <path d={name === 'discrepancy' ? 'M9.5 7h5M7 9.5v5M17 9.5v5M9.5 17h5' : 'M9.5 7h5M7 9.5v5M17 9.5v5M9.5 17h5M12 10v4'} />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20 11.5a8 8 0 0 1-8 8 8.7 8.7 0 0 1-3.1-.6L4 20l1.2-4.3A8 8 0 1 1 20 11.5Z" />
      <path d="M9.8 9.3a2.3 2.3 0 0 1 4.4.8c0 1.7-2.2 2-2.2 3.5M12 16.4h.01" />
    </svg>
  );
}

function MetricIcon({ name }: { name: MetricIconName }) {
  if (name === 'building') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 21V6.5L13 3v18M13 9h7v12M8 8v1M8 12v1M8 16v1M17 12v1M17 16v1M2 21h20" />
      </svg>
    );
  }
  if (name === 'warning') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M10.4 4.4 2.9 18a1.5 1.5 0 0 0 1.3 2.2h15.6a1.5 1.5 0 0 0 1.3-2.2L13.6 4.4a1.8 1.8 0 0 0-3.2 0Z" />
        <path d="M12 9v4.5M12 17h.01" />
      </svg>
    );
  }
  if (name === 'empty-package') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" /><path d="m4.3 7.7 7.7 4.4 7.7-4.4M12 12.1V21M15.5 5l-7.8 4.5" />
        <circle cx="18.5" cy="17.5" r="3.2" /><path d="m17.4 16.4 2.2 2.2M19.6 16.4l-2.2 2.2" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" /><path d="m4.3 7.7 7.7 4.4 7.7-4.4M12 12.1V21M15.5 5l-7.8 4.5" />
    </svg>
  );
}

function HeroPackage() {
  return (
    <svg className="hero-package" viewBox="0 0 180 150" aria-hidden="true">
      <defs>
        <linearGradient id="boxTop" x1="0" x2="1"><stop stopColor="#d6b5ff" /><stop offset="1" stopColor="#8d48ee" /></linearGradient>
        <linearGradient id="boxFront" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#9858ee" /><stop offset="1" stopColor="#5420ac" /></linearGradient>
        <linearGradient id="boxSide" x1="0" x2="1"><stop stopColor="#7335cb" /><stop offset="1" stopColor="#371078" /></linearGradient>
        <filter id="boxGlow"><feGaussianBlur stdDeviation="5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      <ellipse cx="100" cy="132" rx="67" ry="10" fill="#160047" opacity=".5" />
      <g filter="url(#boxGlow)">
        <path d="m37 63 65-34 48 26-65 35Z" fill="url(#boxTop)" />
        <path d="m37 63 48 27v50l-48-27Z" fill="url(#boxFront)" />
        <path d="m85 90 65-35v50l-65 35Z" fill="url(#boxSide)" />
        <path d="m67 47 48 26v50" fill="none" stroke="#e5d1ff" strokeWidth="2" opacity=".65" />
        <path d="m115 73 20-11v19l-20 11Z" fill="#bd8bff" opacity=".75" />
      </g>
      <path d="M26 120h126l12 8H38Z" fill="#8e4ae3" opacity=".65" />
      <path d="M37 129h126l-10 7H28Z" fill="#5220a5" />
    </svg>
  );
}

function LocationCard({
  icon,
  title,
  subtitle,
  active = false,
  onClick,
}: {
  icon: string;
  title: string;
  subtitle: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button className={`location-card ${active ? 'active' : ''}`} onClick={onClick} aria-pressed={active}>
      <span>{icon}</span>
      <div><strong>{title}</strong><small>{subtitle}</small></div>
    </button>
  );
}

function MetricCard({ icon, label, value, note, tone, growth }: { icon: MetricIconName; label: string; value: string; note: string; tone: string; growth?: string }) {
  return (
    <article className="metric-card">
      <span className={`metric-icon ${tone}`}><MetricIcon name={icon} /></span>
      <div className="metric-copy">
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
      {growth && <em>↑ {growth}</em>}
      <p>{note}</p>
    </article>
  );
}

function StatusPill({ status }: { status: StockStatus }) {
  const tone = status === 'Healthy' ? 'healthy' : status === 'Low' ? 'low' : status === 'Excess' ? 'excess' : 'out';
  return <span className={`status-pill ${tone}`}><i />{status}</span>;
}

type WriteOffItem = {
  id: string;
  title: string;
  reasonType: 'DAMAGE' | 'THEFT' | 'EXPIRY';
  aboveLimit: boolean;
  sku: string;
  location: string;
  batch?: string;
  operator: string;
  age: string;
  value: string;
  quantity: string;
  reason: string;
  evidence: string[];
};

const writeOffItems: WriteOffItem[] = [
  {
    id: 'FRZ-PEAS-500',
    title: 'Frozen Green Peas 500g',
    reasonType: 'DAMAGE',
    aboveLimit: true,
    sku: 'FRZ-PEAS-500',
    location: 'DC-BLR-01',
    batch: 'B-2455',
    operator: 'op.kumar',
    age: '11h ago',
    value: '₹43,520',
    quantity: '640 × ₹68.00',
    reason: 'Freezer bay 2 lost power overnight; full pallet thawed.',
    evidence: ['902-a.jpg'],
  },
  {
    id: 'HHD-SOAP-125',
    title: 'Bath Soap 125g',
    reasonType: 'THEFT',
    aboveLimit: true,
    sku: 'HHD-SOAP-125',
    location: 'DS-IND-07',
    operator: 'op.rahul',
    age: '20h ago',
    value: '₹39,600',
    quantity: '1,200 × ₹33.00',
    reason: 'Stock missing after cycle count verification.',
    evidence: ['903-a.jpg'],
  },
  {
    id: 'DRY-MILK-1L',
    title: 'Toned Milk 1L',
    reasonType: 'EXPIRY',
    aboveLimit: false,
    sku: 'DRY-MILK-1L',
    location: 'DS-KOR-04',
    batch: 'B-2502',
    operator: 'op.fatima',
    age: '6h ago',
    value: '₹4,992',
    quantity: '96 × ₹52.00',
    reason: 'Batch crossed use-by on 25 Jul.',
    evidence: ['901-a.jpg', '901-b.jpg'],
  },
  {
    id: 'BAK-BREAD-400',
    title: 'Whole Wheat Bread 400g',
    reasonType: 'DAMAGE',
    aboveLimit: false,
    sku: 'BAK-BREAD-400',
    location: 'DS-HSR-02',
    batch: 'B-2519',
    operator: 'op.sneha',
    age: '2h ago',
    value: '₹880',
    quantity: '22 × ₹40.00',
    reason: 'Crushed in transit crate.',
    evidence: ['904-a.jpg'],
  },
];

function WriteOffActionIcon({ name }: { name: 'refresh' | 'photo' | 'approve' | 'reject' | 'admin' }) {
  if (name === 'refresh') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6.1 8.2A7 7 0 0 1 18.7 10M17.9 15.8A7 7 0 0 1 5.3 14" /></svg>;
  }
  if (name === 'photo') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="4.5" width="17" height="15" rx="2" /><circle cx="9" cy="10" r="2" /><path d="m5.5 17 4.2-4 3.1 2.6 2.5-2.2 3.2 3.6" /></svg>;
  }
  if (name === 'approve') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16.5 8.5" /></svg>;
  }
  if (name === 'admin') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4" /><rect x="4" y="15" width="16" height="6" rx="2" /></svg>;
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6M15 9l-6 6" /></svg>;
}

function WriteOffApprovals({
  activeLocation,
  showToast,
}: {
  activeLocation: string;
  showToast: (message: string) => void;
}) {
  const [decisions, setDecisions] = useState<Record<string, 'approved' | 'rejected' | 'escalated'>>({});
  const [refreshedAt, setRefreshedAt] = useState('Just now');

  const visibleItems = useMemo(
    () => writeOffItems.filter(item => activeLocation === 'All Locations' || item.location === activeLocation),
    [activeLocation]
  );

  const decide = (item: WriteOffItem, decision: 'approved' | 'rejected' | 'escalated') => {
    setDecisions(current => ({ ...current, [item.id]: decision }));
    const message = decision === 'approved'
      ? `${item.title} approved`
      : decision === 'rejected'
        ? `${item.title} rejected`
        : `${item.title} sent to Admin`;
    showToast(message);
  };

  return (
    <section className="writeoff-page">
      <div className="writeoff-heading">
        <div>
          <span className="writeoff-kicker">INVENTORY CONTROL</span>
          <h2>Write-off Approvals</h2>
          <p>Operator-flagged damage, expiry and shrinkage awaiting your decision.</p>
        </div>
        <button onClick={() => {
          setRefreshedAt('Just now');
          showToast('Write-off requests refreshed');
        }}>
          <WriteOffActionIcon name="refresh" />
          Refresh
        </button>
      </div>

      <div className="demo-notice writeoff-demo">
        <span>△</span>
        <strong>Demo data.</strong>
        <p>The manager API is not available on this environment, so these figures come from local fixtures and actions are not persisted.</p>
        <small>Updated {refreshedAt}</small>
      </div>

      <div className="writeoff-summary panel">
        <div><strong>4</strong><span>pending</span></div>
        <i />
        <p>Total value <strong>₹88,992</strong></p>
        <i />
        <em>2 above your approval ceiling — Admin decision required</em>
      </div>

      <div className="writeoff-list">
        {visibleItems.map(item => {
          const decision = decisions[item.id];
          return (
            <article className={`writeoff-card panel${decision ? ` decided ${decision}` : ''}`} key={item.id}>
              <div className="writeoff-card-head">
                <div>
                  <div className="writeoff-title-line">
                    <h3>{item.title}</h3>
                    <span className={`reason-tag ${item.reasonType.toLowerCase()}`}>{item.reasonType}</span>
                    {item.aboveLimit && <span className="limit-tag">Above your limit</span>}
                  </div>
                  <p>
                    <span>{item.sku}</span><i>•</i><span>{item.location}</span>
                    {item.batch && <><i>•</i><span>batch {item.batch}</span></>}
                    <i>•</i><span>raised by {item.operator}</span><span>{item.age}</span>
                  </p>
                </div>
                <div className="writeoff-value"><strong>{item.value}</strong><small>{item.quantity}</small></div>
              </div>

              <div className="writeoff-reason">{item.reason}</div>

              <div className="evidence-block">
                <span>PHOTO EVIDENCE</span>
                <div>
                  {item.evidence.map(file => (
                    <button key={file} onClick={() => showToast(`${file} opened`)}>
                      <WriteOffActionIcon name="photo" />
                      <small>{file}</small>
                    </button>
                  ))}
                </div>
              </div>

              <div className="writeoff-actions">
                <div>
                  {item.aboveLimit ? (
                    <button className="primary" onClick={() => decide(item, 'escalated')} disabled={Boolean(decision)}>
                      <WriteOffActionIcon name="admin" />Send to Admin
                    </button>
                  ) : (
                    <button className="primary" onClick={() => decide(item, 'approved')} disabled={Boolean(decision)}>
                      <WriteOffActionIcon name="approve" />Approve
                    </button>
                  )}
                  <button className="secondary danger" onClick={() => decide(item, 'rejected')} disabled={Boolean(decision)}>
                    <WriteOffActionIcon name="reject" />Reject
                  </button>
                </div>
                {decision ? (
                  <span className={`decision-label ${decision}`}>{decision === 'escalated' ? 'Sent to Admin' : decision}</span>
                ) : (
                  <p>{item.aboveLimit ? 'Quantity exceeds your 500-unit ceiling' : 'Within your ceiling of ₹25,000 / 200 units'}</p>
                )}
              </div>
            </article>
          );
        })}

        {visibleItems.length === 0 && (
          <div className="writeoff-empty panel">
            <strong>No pending requests</strong>
            <p>There are no write-off approvals for {activeLocation}.</p>
          </div>
        )}
      </div>
    </section>
  );
}

type DiscrepancyItem = {
  id: string;
  title: string;
  sku: string;
  location: string;
  value: string;
  variance: number;
  systemQty: number;
  countedQty: number;
  variancePercent: string;
  valueImpact: string;
  cycle: string;
  round: number;
  operator: string;
  age: string;
  note: string;
  recount?: string;
};

const discrepancyItems: DiscrepancyItem[] = [
  {
    id: 'DRY-MILK-1L',
    title: 'Toned Milk 1L',
    sku: 'DRY-MILK-1L',
    location: 'DS-KOR-04',
    value: '₹4,992',
    variance: -96,
    systemQty: 500,
    countedQty: 404,
    variancePercent: '-19.2%',
    valueImpact: '-₹4,992',
    cycle: 'CC-2026-0714',
    round: 2,
    operator: 'op.fatima',
    age: '6h ago',
    note: 'Second count remains below the expected shelf quantity.',
    recount: 'Recount #2',
  },
  {
    id: 'BEV-COLA-500',
    title: 'Cola 500ml',
    sku: 'BEV-COLA-500',
    location: 'DC-BLR-01',
    value: '₹3,999',
    variance: -186,
    systemQty: 900,
    countedQty: 714,
    variancePercent: '-20.7%',
    valueImpact: '-₹3,999',
    cycle: 'CC-2026-0713',
    round: 2,
    operator: 'op.arjun',
    age: '9h ago',
    note: 'Count is short against the receiving and dispatch movements.',
  },
  {
    id: 'HHD-SOAP-125',
    title: 'Bath Soap 125g',
    sku: 'HHD-SOAP-125',
    location: 'DS-IND-07',
    value: '₹1,716',
    variance: 52,
    systemQty: 100,
    countedQty: 152,
    variancePercent: '+52.0%',
    valueImpact: '+₹1,716',
    cycle: 'CC-2026-0712',
    round: 2,
    operator: 'op.rahul',
    age: '18h ago',
    note: 'Additional stock was found in the reserve shelf.',
  },
  {
    id: 'FRZ-PEAS-500',
    title: 'Frozen Green Peas 500g',
    sku: 'FRZ-PEAS-500',
    location: 'DS-IND-07',
    value: '₹884',
    variance: -13,
    systemQty: 74,
    countedQty: 61,
    variancePercent: '-17.6%',
    valueImpact: '-₹884',
    cycle: 'CC-2026-0711',
    round: 3,
    operator: 'op.rahul',
    age: '1d ago',
    note: 'Third count in a row short at this bin.',
    recount: 'Recount #3',
  },
  {
    id: 'BAK-BREAD-400',
    title: 'Whole Wheat Bread 400g',
    sku: 'BAK-BREAD-400',
    location: 'DS-HSR-02',
    value: '₹560',
    variance: -14,
    systemQty: 80,
    countedQty: 66,
    variancePercent: '-17.5%',
    valueImpact: '-₹560',
    cycle: 'CC-2026-0710',
    round: 2,
    operator: 'op.sneha',
    age: '2d ago',
    note: 'Short count remains after checking the damaged-goods crate.',
  },
];

function InsightIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3 13.5 8.5 19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" />
      <path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" />
    </svg>
  );
}

function DiscrepancyQueue({
  activeLocation,
  showToast,
}: {
  activeLocation: string;
  showToast: (message: string) => void;
}) {
  const [selectedId, setSelectedId] = useState('FRZ-PEAS-500');
  const [decisions, setDecisions] = useState<Record<string, 'approved' | 'recount' | 'escalated'>>({});

  const visibleItems = useMemo(
    () => discrepancyItems.filter(item => activeLocation === 'All Locations' || item.location === activeLocation),
    [activeLocation]
  );
  const selected = visibleItems.find(item => item.id === selectedId) ?? visibleItems[0];

  const decide = (decision: 'approved' | 'recount' | 'escalated') => {
    if (!selected) return;
    setDecisions(current => ({ ...current, [selected.id]: decision }));
    const message = decision === 'approved'
      ? `${selected.title} count approved`
      : decision === 'recount'
        ? `Recount requested for ${selected.title}`
        : `${selected.title} escalated to Admin`;
    showToast(message);
  };

  return (
    <section className="discrepancy-page">
      <div className="writeoff-heading">
        <div>
          <span className="writeoff-kicker">INVENTORY CONTROL</span>
          <h2>Discrepancy Review Queue</h2>
          <p>Counts flagged above the variance threshold, highest value first.</p>
        </div>
        <button onClick={() => showToast('Discrepancy queue refreshed')}>
          <WriteOffActionIcon name="refresh" />
          Refresh
        </button>
      </div>

      <div className="demo-notice writeoff-demo">
        <span>△</span>
        <strong>Demo data.</strong>
        <p>The manager API is not available on this environment, so these figures come from local fixtures and actions are not persisted.</p>
      </div>

      <div className="discrepancy-summary panel">
        <div><strong>{visibleItems.length}</strong><span>awaiting review</span></div>
        <i />
        <p>Total variance exposure <strong>₹12,151</strong></p>
      </div>

      {selected ? (
        <div className="discrepancy-workspace">
          <aside className="queue-panel panel">
            <div className="queue-title"><span>INBOX</span><strong>{visibleItems.length}</strong></div>
            <div className="queue-list">
              {visibleItems.map(item => (
                <button
                  key={item.id}
                  className={selected.id === item.id ? 'active' : ''}
                  onClick={() => setSelectedId(item.id)}
                >
                  <div>
                    <strong>{item.title}</strong>
                    <em className={item.variance > 0 ? 'positive' : 'negative'}>{item.variance > 0 ? '+' : ''}{item.variance}</em>
                  </div>
                  <p><span>{item.sku}</span><i>•</i><span>{item.location}</span><i>•</i><span>{item.value}</span></p>
                  {item.recount && <small>{item.recount}</small>}
                </button>
              ))}
            </div>
          </aside>

          <article className="discrepancy-detail panel">
            <div className="discrepancy-detail-head">
              <div>
                <h3>{selected.title}</h3>
                <p><span>{selected.sku}</span><i>•</i><span>{selected.location}</span><i>•</i><span>{selected.cycle}</span></p>
              </div>
              <div className="review-tags"><span>Pending review</span><b>Round {selected.round}</b></div>
            </div>

            <div className="discrepancy-metrics">
              <article><span>SYSTEM QTY</span><strong>{selected.systemQty}</strong></article>
              <article><span>COUNTED QTY</span><strong>{selected.countedQty}</strong></article>
              <article className={selected.variance > 0 ? 'positive' : 'negative'}><span>VARIANCE</span><strong>{selected.variance > 0 ? '+' : ''}{selected.variance} ({selected.variancePercent})</strong></article>
              <article className={selected.variance > 0 ? 'positive' : 'negative'}><span>VALUE IMPACT</span><strong>{selected.valueImpact}</strong></article>
            </div>

            <div className="count-note">
              <div><span>Counted by <strong>{selected.operator}</strong></span><small>{selected.age}</small></div>
              <p>{selected.note}</p>
            </div>

            <div className="ai-insight">
              <span><InsightIcon /></span>
              <div><strong>AI Insight</strong><p>{selected.round >= 3
                ? 'Third consecutive count at this bin. Repeated variance usually means a process issue — consider escalating rather than approving.'
                : selected.variance > 0
                  ? 'The positive variance may indicate an unrecorded stock transfer. Verify the most recent inbound movement before approval.'
                  : 'The repeated short count should be compared with recent dispatch, damage and transfer activity before approval.'}</p></div>
            </div>

            <div className="discrepancy-actions">
              <button className="approve" disabled={Boolean(decisions[selected.id])} onClick={() => decide('approved')}><WriteOffActionIcon name="approve" />Approve count</button>
              <button className="recount" disabled={Boolean(decisions[selected.id])} onClick={() => decide('recount')}><WriteOffActionIcon name="refresh" />Reject / recount</button>
              <button className="escalate" disabled={Boolean(decisions[selected.id])} onClick={() => decide('escalated')}><WriteOffActionIcon name="admin" />Escalate to Admin</button>
              {decisions[selected.id] && <span className={`decision-label ${decisions[selected.id]}`}>{decisions[selected.id] === 'recount' ? 'Recount requested' : decisions[selected.id]}</span>}
            </div>
          </article>
        </div>
      ) : (
        <div className="writeoff-empty panel">
          <strong>No discrepancies found</strong>
          <p>There are no flagged counts for {activeLocation}.</p>
        </div>
      )}
    </section>
  );
}

type ReservationStatus = 'Active' | 'Released';

type ReservationItem = {
  id: string;
  location: string;
  sku: string;
  product: string;
  quantity: number;
  orderRef: string;
  created: string;
  expires: string;
  status: ReservationStatus;
  bin: string;
  reservedFor: string;
  reason: string;
  owner: string;
  source: string;
};

const reservationFixtures: ReservationItem[] = [
  {
    id: 'RSV-88540',
    location: 'DS-IND-07',
    sku: 'FRZ-PEAS-500',
    product: 'Frozen Green Peas 500g',
    quantity: 22,
    orderRef: 'ORD-88540',
    created: '27 Jul, 09:23 am',
    expires: 'in 55m',
    status: 'Active',
    bin: 'FRZ-A-14',
    reservedFor: 'Customer order fulfillment',
    reason: 'Inventory held while the active discrepancy review is completed.',
    owner: 'op.rahul',
    source: 'Inventory exception',
  },
  {
    id: 'RSV-88213',
    location: 'DS-KOR-04',
    sku: 'BEV-COLA-500',
    product: 'Cola 500ml',
    quantity: 24,
    orderRef: 'ORD-88213',
    created: '26 Jul, 04:23 am',
    expires: 'in 59m',
    status: 'Active',
    bin: 'BEV-C-07',
    reservedFor: 'Customer order fulfillment',
    reason: 'Order allocation is protected while payment verification completes.',
    owner: 'op.fatima',
    source: 'Order allocation',
  },
  {
    id: 'RSV-88602',
    location: 'DS-HSR-02',
    sku: 'BAK-BREAD-400',
    product: 'Whole Wheat Bread 400g',
    quantity: 36,
    orderRef: 'ORD-88602',
    created: '27 Jul, 09:53 am',
    expires: 'in 2h',
    status: 'Active',
    bin: 'BAK-B-12',
    reservedFor: 'Dispatch wave W-219',
    reason: 'Picker assigned; inventory is protected until the dispatch window closes.',
    owner: 'op.sneha',
    source: 'Warehouse dispatch',
  },
  {
    id: 'RSV-4471',
    location: 'DC-BLR-01',
    sku: 'SNK-CHIP-100',
    product: 'Potato Chips 100g',
    quantity: 310,
    orderRef: 'TRF-4471',
    created: '26 Jul, 08:23 pm',
    expires: '2h ago',
    status: 'Released',
    bin: 'SNK-A-03',
    reservedFor: 'Inter-location transfer',
    reason: 'Hold released after transfer cancellation was confirmed.',
    owner: 'system',
    source: 'Transfer workflow',
  },
];

function ReservationIcon({ name }: { name: 'hold' | 'units' | 'timer' | 'released' | 'search' | 'box' }) {
  if (name === 'search') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m15.5 15.5 4 4" /></svg>;
  }
  if (name === 'timer') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="13" r="8" /><path d="M9 3h6M12 9v4l3 2" /></svg>;
  }
  if (name === 'released') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16.5 8.5" /></svg>;
  }
  if (name === 'units') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Z" /><path d="m4.3 7.7 7.7 4.4 7.7-4.4M12 12.1V21" /></svg>;
  }
  if (name === 'box') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="14" rx="2" /><path d="M8 9h8M8 13h5" /></svg>;
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 11V8a5 5 0 0 1 10 0v3" /><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M12 15v2" /></svg>;
}

function ReservationOverrides({
  activeLocation,
  showToast,
}: {
  activeLocation: string;
  showToast: (message: string) => void;
}) {
  const [reservations, setReservations] = useState(reservationFixtures);
  const [selectedId, setSelectedId] = useState('RSV-88540');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'All' | ReservationStatus>('All');

  const visibleItems = useMemo(
    () => reservations.filter(item => {
      const matchesLocation = activeLocation === 'All Locations' || item.location === activeLocation;
      const matchesStatus = statusFilter === 'All' || item.status === statusFilter;
      const matchesSearch = `${item.sku} ${item.product} ${item.orderRef}`.toLowerCase().includes(search.toLowerCase());
      return matchesLocation && matchesStatus && matchesSearch;
    }),
    [activeLocation, reservations, search, statusFilter]
  );

  const selected = visibleItems.find(item => item.id === selectedId) ?? visibleItems[0];
  const activeReservations = reservations.filter(item => item.status === 'Active');
  const activeUnits = activeReservations.reduce((total, item) => total + item.quantity, 0);
  const releasedCount = reservations.filter(item => item.status === 'Released').length;

  const updateReservation = (id: string, update: Partial<ReservationItem>) => {
    setReservations(current => current.map(item => item.id === id ? { ...item, ...update } : item));
  };

  const forceRelease = (item: ReservationItem) => {
    updateReservation(item.id, { status: 'Released', expires: 'Just now' });
    showToast(`${item.product} reservation released`);
  };

  const extendHold = (item: ReservationItem) => {
    updateReservation(item.id, { expires: 'in 1h 55m' });
    showToast(`${item.product} hold extended by 1 hour`);
  };

  return (
    <section className="reservation-page">
      <div className="writeoff-heading">
        <div>
          <span className="writeoff-kicker">INVENTORY CONTROL</span>
          <h2>Reservation Overrides</h2>
          <p>Force-release or extend holds that are stuck at your locations.</p>
        </div>
        <button onClick={() => showToast('Reservation holds refreshed')}>
          <WriteOffActionIcon name="refresh" />
          Refresh
        </button>
      </div>

      <div className="demo-notice writeoff-demo">
        <span>△</span>
        <strong>Demo data.</strong>
        <p>The manager API is not available on this environment, so these figures come from local fixtures and actions are not persisted.</p>
      </div>

      <div className="reservation-stats">
        <article className="panel purple"><span><ReservationIcon name="hold" /></span><div><small>ACTIVE HOLDS</small><strong>{activeReservations.length}</strong><p>Across assigned locations</p></div></article>
        <article className="panel blue"><span><ReservationIcon name="units" /></span><div><small>RESERVED UNITS</small><strong>{activeUnits}</strong><p>Currently unavailable to sell</p></div></article>
        <article className="panel orange"><span><ReservationIcon name="timer" /></span><div><small>EXPIRING SOON</small><strong>2</strong><p>Within the next hour</p></div></article>
        <article className="panel green"><span><ReservationIcon name="released" /></span><div><small>RELEASED TODAY</small><strong>{releasedCount}</strong><p>Manual and automatic releases</p></div></article>
      </div>

      <div className="reservation-toolbar panel">
        <div className="reservation-search">
          <ReservationIcon name="search" />
          <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search SKU, product or order reference…" />
        </div>
        <div className="reservation-filters">
          {(['All', 'Active', 'Released'] as const).map(status => (
            <button key={status} className={statusFilter === status ? 'active' : ''} onClick={() => setStatusFilter(status)}>{status}</button>
          ))}
        </div>
      </div>

      <div className="reservation-layout">
        <article className="reservation-table-panel panel">
          <div className="reservation-table-wrap">
            <table className="reservation-table">
              <thead><tr><th>LOCATION</th><th>PRODUCT</th><th>QTY</th><th>ORDER REF</th><th>CREATED</th><th>EXPIRES</th><th>STATUS</th><th>OVERRIDE</th></tr></thead>
              <tbody>
                {visibleItems.map(item => (
                  <tr key={item.id} className={selected?.id === item.id ? 'selected' : ''}>
                    <td><strong>{item.location}</strong></td>
                    <td>
                      <button className="reservation-product" onClick={() => setSelectedId(item.id)}>
                        <span><ReservationIcon name="box" /></span>
                        <div><strong>{item.product}</strong><small>{item.sku}</small></div>
                      </button>
                    </td>
                    <td><strong>{item.quantity}</strong></td>
                    <td><span className="order-ref">{item.orderRef}</span></td>
                    <td>{item.created}</td>
                    <td className={item.status === 'Released' ? 'expired' : 'expires'}>{item.expires}</td>
                    <td><span className={`reservation-status ${item.status.toLowerCase()}`}><i />{item.status}</span></td>
                    <td>
                      <div className="reservation-row-actions">
                        <button disabled={item.status === 'Released'} onClick={() => forceRelease(item)}>Force release</button>
                        <button disabled={item.status === 'Released'} onClick={() => extendHold(item)}>Extend hold</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {visibleItems.length === 0 && <tr className="empty-row"><td colSpan={8}>No reservations match the selected filters.</td></tr>}
              </tbody>
            </table>
          </div>
        </article>

        {selected && (
          <aside className="reservation-detail panel">
            <div className="reservation-detail-head">
              <span><ReservationIcon name="hold" /></span>
              <div><small>SELECTED HOLD</small><h3>{selected.product}</h3><p>{selected.sku}</p></div>
              <b className={`reservation-status ${selected.status.toLowerCase()}`}><i />{selected.status}</b>
            </div>

            <div className="reservation-detail-grid">
              <div><small>ORDER REFERENCE</small><strong>{selected.orderRef}</strong></div>
              <div><small>LOCATION / BIN</small><strong>{selected.location} · {selected.bin}</strong></div>
              <div><small>QUANTITY</small><strong>{selected.quantity} units</strong></div>
              <div><small>EXPIRES</small><strong>{selected.expires}</strong></div>
            </div>

            <div className="hold-context">
              <span>HOLD CONTEXT</span>
              <p>{selected.reason}</p>
              <dl>
                <div><dt>Reserved for</dt><dd>{selected.reservedFor}</dd></div>
                <div><dt>Created by</dt><dd>{selected.owner}</dd></div>
                <div><dt>Source</dt><dd>{selected.source}</dd></div>
                <div><dt>Created</dt><dd>{selected.created}</dd></div>
              </dl>
            </div>

            {selected.status === 'Active' ? (
              <div className="reservation-detail-actions">
                <button className="release" onClick={() => forceRelease(selected)}><WriteOffActionIcon name="reject" />Force release</button>
                <button className="extend" onClick={() => extendHold(selected)}><WriteOffActionIcon name="refresh" />Extend 1 hour</button>
              </div>
            ) : (
              <div className="released-note"><ReservationIcon name="released" /><span>This hold has already been released.</span></div>
            )}
          </aside>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const [mobileNav, setMobileNav] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [search, setSearch] = useState('');
  const [activeLocation, setActiveLocation] = useState('All Locations');
  const [statusFilter, setStatusFilter] = useState<'All' | StockStatus>('All');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; direction: 'asc' | 'desc' }>({ key: 'sku', direction: 'asc' });
  const [openRow, setOpenRow] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [activeView, setActiveView] = useState<ViewName>('Stock Ledger');
  const [toast, setToast] = useState('');
  const toastTimer = useRef<number | null>(null);

  const showToast = (message: string) => {
    setToast(message);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(''), 2600);
  };

  const filteredItems = useMemo(
    () => {
      const rows = stockItems.filter(item => {
        const matchesSearch = `${item.sku} ${item.title} ${item.location}`.toLowerCase().includes(search.toLowerCase());
        const matchesLocation = activeLocation === 'All Locations' || item.location === activeLocation;
        const matchesStatus = statusFilter === 'All' || item.status === statusFilter;
        return matchesSearch && matchesLocation && matchesStatus;
      });

      return [...rows].sort((first, second) => {
        const firstValue = first[sort.key];
        const secondValue = second[sort.key];
        const comparison = typeof firstValue === 'number' && typeof secondValue === 'number'
          ? firstValue - secondValue
          : String(firstValue).localeCompare(String(secondValue));
        return sort.direction === 'asc' ? comparison : -comparison;
      });
    },
    [activeLocation, search, sort, statusFilter]
  );

  const handleSort = (key: SortKey) => {
    setSort(current => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const sortMark = (key: SortKey) => sort.key === key ? (sort.direction === 'asc' ? '↑' : '↓') : '↕';

  const downloadCsv = () => {
    const headings = ['SKU', 'Title', 'Location', 'Inventory', 'Reserved', 'Available', 'Value (INR)', 'Status'];
    const rows = filteredItems.map(item => [
      item.sku, item.title, item.location, item.inventory, item.reserved, item.available, item.value, item.status,
    ]);
    const csv = [headings, ...rows]
      .map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))
      .join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'ims-stock-overview.csv';
    link.click();
    URL.revokeObjectURL(url);
    showToast('Stock overview downloaded');
  };

  return (
    <div className={`ims-app${darkMode ? ' dark' : ''}${sidebarCollapsed ? ' sidebar-is-collapsed' : ''}`}>
      {mobileNav && <button className="mobile-overlay" onClick={() => setMobileNav(false)} />}
      <aside className={mobileNav ? 'sidebar open' : 'sidebar'}>
        <div className="sidebar-brand">
          <img src="/accesco-logo.png" alt="Accesco" />
          <div><strong>Accesco</strong><small>LIVING, REDEFINED</small></div>
          <button onClick={() => setMobileNav(false)}>×</button>
        </div>

        <section className="manager-card">
          <span>R</span>
          <div><strong>R. Iyer</strong><small>4 assigned locations</small></div>
        </section>

        <nav>
          {navigation.map(({ icon, label }) => (
            <button
              key={label}
              className={activeView === label ? 'active' : ''}
              onClick={() => {
                if (label === 'Stock Ledger' || label === 'Discrepancy Queue' || label === 'Write-off Approvals' || label === 'Reservation Overrides') {
                  setActiveView(label);
                  setMobileNav(false);
                  showToast(`${label} opened`);
                } else {
                  showToast(`${label} will open when its frontend screen is added`);
                }
              }}
            >
              <span><NavIcon name={icon} /></span><b>{label}</b>
            </button>
          ))}
        </nav>

        <section className="support-card">
          <span><HelpIcon /></span>
          <div><strong>Need Help?</strong><p>Check user guide or<br />contact support.</p></div>
          <button onClick={() => showToast('IMS help guide opened')}>View Guide <b>↗</b></button>
        </section>

        <footer>
          <p>© 2026 Accesco Living</p>
          <p>All rights reserved.</p>
          <button onClick={() => setSidebarCollapsed(current => !current)}>{sidebarCollapsed ? '»' : '«'}</button>
        </footer>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <button
            className="hamburger"
            onClick={() => window.innerWidth <= 980
              ? setMobileNav(true)
              : setSidebarCollapsed(current => !current)}
            aria-label="Toggle navigation"
          >
            ☰
          </button>
          <h1>Inventory Management System (IMS)</h1>
          <div className="top-actions">
            <button
              onClick={() => {
                setDarkMode(current => !current);
                showToast(darkMode ? 'Light mode enabled' : 'Dark mode enabled');
              }}
              aria-label="Toggle theme"
            >
              {darkMode ? <SunIcon /> : <MoonIcon />}
            </button>
            <div className="action-wrap">
              <button
                className="notification"
                onClick={() => {
                  setNotificationsOpen(current => !current);
                  setAdminOpen(false);
                }}
                aria-label="Notifications"
              >
                <BellIcon /><i>3</i>
              </button>
              {notificationsOpen && (
                <div className="action-menu notification-menu">
                  <strong>Notifications</strong>
                  <button onClick={() => showToast('Low-stock items opened')}>18 items are running low <small>Just now</small></button>
                  <button onClick={() => showToast('Replenishment alert opened')}>3 items need replenishment <small>8 min ago</small></button>
                  <button onClick={() => showToast('Stock sync details opened')}>Stock sync completed <small>20 min ago</small></button>
                </div>
              )}
            </div>
            <div className="action-wrap">
              <button
                className="admin"
                onClick={() => {
                  setAdminOpen(current => !current);
                  setNotificationsOpen(false);
                }}
              >
                <span>A</span><strong>admin</strong><ChevronIcon />
              </button>
              {adminOpen && (
                <div className="action-menu admin-menu">
                  <button onClick={() => showToast('Profile selected')}>My profile</button>
                  <button onClick={() => showToast('Settings selected')}>Settings</button>
                  <button onClick={() => showToast('Signed out of demo session')}>Sign out</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main>
          <section className="location-row">
            <label>SELECT LOCATION</label>
            <div className="location-scroll">
              {locations.map(location => (
                <LocationCard
                  key={location.title}
                  {...location}
                  active={activeLocation === location.title}
                  onClick={() => {
                    setActiveLocation(location.title);
                    setCurrentPage(1);
                    showToast(`${location.title} selected`);
                  }}
                />
              ))}
            </div>
            {activeView === 'Stock Ledger' && (
              <div className="filter-wrap">
                <button className={`filter-button${statusFilter !== 'All' ? ' has-filter' : ''}`} onClick={() => setFiltersOpen(current => !current)}>
                  <FilterIcon />
                  <strong>Filters</strong>
                  <span className={filtersOpen ? 'chevron-open' : ''}><ChevronIcon /></span>
                </button>
                {filtersOpen && (
                  <div className="filter-menu">
                    <strong>Stock status</strong>
                    {(['All', 'Healthy', 'Low', 'Out of Stock', 'Excess'] as const).map(status => (
                      <button
                        key={status}
                        className={statusFilter === status ? 'active' : ''}
                        onClick={() => {
                          setStatusFilter(status);
                          setCurrentPage(1);
                        }}
                      >
                        <i />{status}
                      </button>
                    ))}
                    <button className="apply-filter" onClick={() => {
                      setFiltersOpen(false);
                      showToast(statusFilter === 'All' ? 'All stock shown' : `${statusFilter} filter applied`);
                    }}>
                      Apply filter
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>

          {activeView === 'Reservation Overrides' ? (
            <ReservationOverrides activeLocation={activeLocation} showToast={showToast} />
          ) : activeView === 'Discrepancy Queue' ? (
            <DiscrepancyQueue activeLocation={activeLocation} showToast={showToast} />
          ) : activeView === 'Write-off Approvals' ? (
            <WriteOffApprovals activeLocation={activeLocation} showToast={showToast} />
          ) : (
            <>
          <section className="overview-grid">
            <article className="ledger-hero">
              <div><h2>Stock Ledger</h2><p>Real-time inventory visibility across all locations</p></div>
              <HeroPackage />
              <b>✦</b><em>✧</em>
            </article>
            <MetricCard icon="package" label="TOTAL SKUS" value="4,583" growth="3%" note="Across all locations" tone="purple" />
            <MetricCard icon="building" label="ACTIVE LOCATIONS" value="4" note="All locations operational" tone="blue" />
            <MetricCard icon="warning" label="LOW STOCK ITEMS" value="18" note="Need attention" tone="orange" />
            <MetricCard icon="empty-package" label="OUT OF STOCK ITEMS" value="3" note="Require replenishment" tone="red" />
          </section>

          <section className="demo-notice">
            <span>△</span>
            <strong>Demo data.</strong>
            <p>The manager API is not available on this environment, so these figures come from local fixtures and actions are not persisted.</p>
          </section>

          <section className="content-grid">
            <aside className="summary-column">
              <article className="inventory-summary panel">
                <h2>Inventory Summary</h2>
                <div className="summary-body">
                  <div className="donut">
                    <div><strong>4,583</strong><small>Total SKUs</small></div>
                  </div>
                  <ul>
                    <li><i className="healthy-dot" /><span>Healthy<strong>3,413 (74.5%)</strong></span></li>
                    <li><i className="low-dot" /><span>Low<strong>842 (18.4%)</strong></span></li>
                    <li><i className="out-dot" /><span>Out of Stock<strong>203 (4.4%)</strong></span></li>
                    <li><i className="excess-dot" /><span>Excess<strong>125 (2.7%)</strong></span></li>
                  </ul>
                </div>
              </article>

              <article className="value-card panel">
                <div><small>Inventory Value (INR)</small><strong>₹ 48,72,350 <em>↑ 8.6%</em></strong><p>vs last 7 days</p></div>
                <svg viewBox="0 0 170 75" preserveAspectRatio="none">
                  <defs><linearGradient id="valueArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7c2ce1" stopOpacity=".25" /><stop offset="1" stopColor="#7c2ce1" stopOpacity="0" /></linearGradient></defs>
                  <path d="M0 62 L28 46 L55 37 L82 47 L111 25 L137 24 L170 6 L170 75 L0 75Z" fill="url(#valueArea)" />
                  <path d="M0 62 L28 46 L55 37 L82 47 L111 25 L137 24 L170 6" fill="none" stroke="#7c2ce1" strokeWidth="3" />
                </svg>
              </article>

              <article className="updated-card panel">
                <div><small>Last Updated</small><strong>Just now</strong><p><i />Real-time sync active</p></div>
                <span>▱</span>
              </article>
            </aside>

            <article className="stock-panel panel">
              <div className="stock-heading">
                <h2>Stock Overview</h2>
                <div className="stock-tools">
                  <label><span>⌕</span><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search SKU, Title or Barcode…" /></label>
                  <button onClick={downloadCsv} aria-label="Download stock overview">⇩</button>
                </div>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th><button onClick={() => handleSort('sku')}>SKU {sortMark('sku')}</button></th>
                      <th><button onClick={() => handleSort('title')}>TITLE {sortMark('title')}</button></th>
                      <th><button onClick={() => handleSort('location')}>LOCATION {sortMark('location')}</button></th>
                      <th><button onClick={() => handleSort('inventory')}>INVENTORY {sortMark('inventory')}</button></th>
                      <th><button onClick={() => handleSort('reserved')}>RESERVED {sortMark('reserved')}</button></th>
                      <th><button onClick={() => handleSort('available')}>AVAILABLE {sortMark('available')}</button></th>
                      <th><button onClick={() => handleSort('value')}>VALUE (INR) {sortMark('value')}</button></th>
                      <th><button onClick={() => handleSort('status')}>STATUS {sortMark('status')}</button></th>
                      <th>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map(item => (
                      <tr key={item.sku}>
                        <td><div className="sku-cell"><span>{item.icon}</span><strong>{item.sku}</strong></div></td>
                        <td><strong>{item.title}</strong></td>
                        <td><strong>{item.location}</strong><small className="type-tag">{item.type}</small></td>
                        <td><strong>{item.inventory.toLocaleString('en-IN')}</strong></td>
                        <td>{item.reserved}</td>
                        <td className={item.status === 'Out of Stock' ? 'available zero' : 'available'}>{item.available.toLocaleString('en-IN')}</td>
                        <td>{item.value}</td>
                        <td><StatusPill status={item.status} /></td>
                        <td className="row-actions">
                          <button className="more-button" onClick={() => setOpenRow(current => current === item.sku ? null : item.sku)}>•••</button>
                          {openRow === item.sku && (
                            <div className="row-menu">
                              <button onClick={() => { setOpenRow(null); showToast(`${item.sku} details opened`); }}>View details</button>
                              <button onClick={() => { setOpenRow(null); showToast(`Stock adjustment started for ${item.sku}`); }}>Adjust stock</button>
                              <button onClick={() => { setOpenRow(null); showToast(`${item.sku} activity opened`); }}>View activity</button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                    {filteredItems.length === 0 && (
                      <tr className="empty-row"><td colSpan={9}>No stock items match the selected filters.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              <footer className="table-footer">
                <p>Showing <strong>1–{filteredItems.length}</strong> of <strong>4,583</strong> items</p>
                <div className="pagination">
                  <div className="rows-control">
                    <span>Rows per page</span>
                    <button
                      className="rows"
                      onClick={() => setRowsPerPage(current => current === 10 ? 20 : current === 20 ? 5 : 10)}
                      aria-label="Change rows per page"
                    >
                      {rowsPerPage}<ChevronIcon />
                    </button>
                  </div>
                  <nav className="page-controls" aria-label="Table pagination">
                    <button className="nav-button" disabled={currentPage === 1} onClick={() => setCurrentPage(1)} aria-label="First page"><PageEdgeIcon direction="first" /></button>
                    <button className="nav-button" disabled={currentPage === 1} onClick={() => setCurrentPage(current => Math.max(1, current - 1))} aria-label="Previous page"><ChevronIcon direction="left" /></button>
                    {[1, 2, 3].map(page => <button key={page} className={`page-button${currentPage === page ? ' active' : ''}`} onClick={() => setCurrentPage(page)}>{page}</button>)}
                    <i>…</i>
                    <button className={`page-button wide${currentPage === 459 ? ' active' : ''}`} onClick={() => setCurrentPage(459)}>459</button>
                    <button className="nav-button" disabled={currentPage === 459} onClick={() => setCurrentPage(current => Math.min(459, current + 1))} aria-label="Next page"><ChevronIcon direction="right" /></button>
                    <button className="nav-button" disabled={currentPage === 459} onClick={() => setCurrentPage(459)} aria-label="Last page"><PageEdgeIcon direction="last" /></button>
                  </nav>
                </div>
              </footer>
            </article>
          </section>
            </>
          )}
        </main>
      </div>
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}