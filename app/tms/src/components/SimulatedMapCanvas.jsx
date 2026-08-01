import React from 'react';
import { Navigation, MapPin, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function SimulatedMapCanvas({
  origin = 'Bengaluru Central Hub',
  destination = 'Pune Fulfilment Center',
  currentLat = 15.3647,
  currentLng = 75.1240,
  speedKmh = 64,
  stops = [],
  exception = null,
  height = '320px',
}) {
  return (
    <div
      style={{
        width: '100%',
        height,
        backgroundColor: '#111827',
        borderRadius: '12px',
        position: 'relative',
        overflow: 'hidden',
        border: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Top Map Status Overlay */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          right: '12px',
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(17, 24, 39, 0.85)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '8px 14px',
          borderRadius: '8px',
          color: '#ffffff',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#16a34a',
              boxShadow: '0 0 8px #16a34a',
            }}
          />
          <span style={{ fontSize: '12px', fontWeight: '600' }}>GPS Live Tracking Vector</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '11px', color: '#9ca3af' }}>
          <span>Lat: {currentLat?.toFixed(4)}° N</span>
          <span>Lng: {currentLng?.toFixed(4)}° E</span>
          <span style={{ color: '#3b82f6', fontWeight: '700' }}>Speed: {speedKmh} KM/H</span>
        </div>
      </div>

      {/* SVG Vector Route Canvas */}
      <svg
        width="100%"
        height="100%"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        {/* Background Grid Lines */}
        <defs>
          <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#gridPattern)" />

        {/* Route Line */}
        <path
          d="M 80 220 Q 240 80, 480 180 T 800 140"
          fill="none"
          stroke="#2563eb"
          strokeWidth="4"
          strokeDasharray="8 4"
        />

        {/* Origin Node */}
        <g transform="translate(80, 220)">
          <circle r="12" fill="#1e40af" stroke="#ffffff" strokeWidth="2" />
          <circle r="5" fill="#ffffff" />
          <text x="0" y="28" fill="#ffffff" fontSize="11" fontWeight="700" textAnchor="middle">
            {origin}
          </text>
        </g>

        {/* Intermediate Stop Nodes */}
        {stops.map((st, i) => {
          const x = 260 + i * 160;
          const y = 120 + i * 40;
          return (
            <g key={i} transform={`translate(${x}, ${y})`}>
              <circle r="8" fill="#374151" stroke="#3b82f6" strokeWidth="2" />
              <text x="0" y="22" fill="#9ca3af" fontSize="10" textAnchor="middle">
                {st.name || `Stop ${i + 1}`}
              </text>
            </g>
          );
        })}

        {/* Current Vehicle Position */}
        <g transform="translate(480, 180)">
          <circle r="22" fill="rgba(37, 99, 235, 0.25)" />
          <circle r="14" fill="#2563eb" stroke="#ffffff" strokeWidth="2" />
          <polygon points="0,-6 6,6 -6,6" fill="#ffffff" transform="rotate(45)" />
          <text x="0" y="-22" fill="#60a5fa" fontSize="11" fontWeight="700" textAnchor="middle">
            ACTIVE ASSET ({speedKmh} KM/H)
          </text>
        </g>

        {/* Exception Marker if active */}
        {exception && (
          <g transform="translate(540, 160)">
            <circle r="16" fill="rgba(239, 68, 68, 0.3)" />
            <polygon points="0,-10 10,8 -10,8" fill="#ef4444" />
            <text x="0" y="24" fill="#f87171" fontSize="10" fontWeight="700" textAnchor="middle">
              {exception}
            </text>
          </g>
        )}

        {/* Destination Node */}
        <g transform="translate(800, 140)">
          <circle r="12" fill="#16a34a" stroke="#ffffff" strokeWidth="2" />
          <circle r="5" fill="#ffffff" />
          <text x="0" y="28" fill="#ffffff" fontSize="11" fontWeight="700" textAnchor="middle">
            {destination}
          </text>
        </g>
      </svg>

      {/* Bottom Map Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: '12px',
          left: '12px',
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          background: 'rgba(17, 24, 39, 0.85)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '6px 12px',
          borderRadius: '6px',
          color: '#ffffff',
          fontSize: '11px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#1e40af' }} />
          <span>Origin Hub</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#2563eb' }} />
          <span>Vehicle En Route</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#16a34a' }} />
          <span>Destination</span>
        </div>
      </div>
    </div>
  );
}
