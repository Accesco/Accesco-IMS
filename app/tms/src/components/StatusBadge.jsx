import React from 'react';

export default function StatusBadge({ status, type = 'default' }) {
  let colorClass = 'badge-gray';

  const s = String(status || '').toLowerCase();

  if (s.includes('active') || s.includes('delivered') || s.includes('passed') || s.includes('accepted') || s.includes('healthy') || s.includes('validated') || s.includes('allocated') || s.includes('awarded') || s.includes('resolved') || s.includes('completed')) {
    colorClass = 'badge-green';
  } else if (s.includes('transit') || s.includes('assigned') || s.includes('bidding') || s.includes('planned') || s.includes('consolidating')) {
    colorClass = 'badge-blue';
  } else if (s.includes('unallocated') || s.includes('tendering') || s.includes('awaiting') || s.includes('warning') || s.includes('hold') || s.includes('variance') || s.includes('review') || s.includes('spot auction')) {
    colorClass = 'badge-orange';
  } else if (s.includes('exception') || s.includes('failed') || s.includes('rejected') || s.includes('timed out') || s.includes('breach') || s.includes('human dispatch') || s.includes('critical') || s.includes('degraded')) {
    colorClass = 'badge-red';
  } else if (s.includes('reefer') || s.includes('dedicated')) {
    colorClass = 'badge-purple';
  } else if (s.includes('received') || s.includes('ltl') || s.includes('ftl')) {
    colorClass = 'badge-cyan';
  }

  return (
    <span className={`status-badge ${colorClass}`}>
      <span className="badge-dot" />
      {status}
    </span>
  );
}
