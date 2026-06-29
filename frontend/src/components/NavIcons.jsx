// Custom thin-line SVG icons for the sidebar nav.
//
// All icons share one stroke style (1.6px, round caps/joins, currentColor) so
// they inherit the nav item's text color — muted by default, brand text/cyan
// when the item is active. 22×22 viewBox, sized via the `size` prop.

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function Svg({ size = 18, children, label }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 22 22"
      role="img"
      aria-label={label}
      style={{ display: "block" }}
    >
      {children}
    </svg>
  );
}

// Overview — dashboard grid
export function OverviewIcon({ size }) {
  return (
    <Svg size={size} label="Overview">
      <rect x="3" y="3" width="7" height="7" rx="1.5" {...base} />
      <rect x="12" y="3" width="7" height="5" rx="1.5" {...base} />
      <rect x="12" y="11" width="7" height="8" rx="1.5" {...base} />
      <rect x="3" y="13" width="7" height="6" rx="1.5" {...base} />
    </Svg>
  );
}

// Scan — radar / signal sweep
export function ScanIcon({ size }) {
  return (
    <Svg size={size} label="Scan">
      <path d="M11 11 L18 6" {...base} />
      <path d="M4.5 16.5a9 9 0 1 1 13 0" {...base} />
      <path d="M7.5 14a5 5 0 1 1 7 0" {...base} />
      <circle cx="11" cy="11" r="1.1" fill="currentColor" stroke="none" />
    </Svg>
  );
}

// Issues — warning triangle
export function IssuesIcon({ size }) {
  return (
    <Svg size={size} label="Issues">
      <path d="M11 3.5 L19.5 18 H2.5 Z" {...base} />
      <path d="M11 9 V13" {...base} />
      <circle cx="11" cy="15.6" r="0.6" fill="currentColor" stroke="none" />
    </Svg>
  );
}

// AI Fix Assistant — spark / sparkle
export function AiIcon({ size }) {
  return (
    <Svg size={size} label="AI Assistant">
      <path d="M11 3 C11.6 6.6 12.4 7.4 16 8 C12.4 8.6 11.6 9.4 11 13 C10.4 9.4 9.6 8.6 6 8 C9.6 7.4 10.4 6.6 11 3 Z" {...base} />
      <path d="M16.5 13 C16.8 14.6 17.2 15 18.8 15.3 C17.2 15.6 16.8 16 16.5 17.6 C16.2 16 15.8 15.6 14.2 15.3 C15.8 15 16.2 14.6 16.5 13 Z" {...base} />
    </Svg>
  );
}

// Reports — document with lines
export function ReportsIcon({ size }) {
  return (
    <Svg size={size} label="Reports">
      <path d="M6 3 H13 L17 7 V19 H6 Z" {...base} />
      <path d="M13 3 V7 H17" {...base} />
      <path d="M8.5 11 H14" {...base} />
      <path d="M8.5 14 H14" {...base} />
      <path d="M8.5 16.5 H11.5" {...base} />
    </Svg>
  );
}

// History — clock with arrow
export function HistoryIcon({ size }) {
  return (
    <Svg size={size} label="History">
      <path d="M3.5 11 a7.5 7.5 0 1 0 2.4-5.5" {...base} />
      <path d="M3.2 4 V7.5 H6.7" {...base} />
      <path d="M11 7.5 V11 L13.5 12.8" {...base} />
    </Svg>
  );
}

// Settings — gear
export function SettingsIcon({ size }) {
  return (
    <Svg size={size} label="Settings">
      <circle cx="11" cy="11" r="2.6" {...base} />
      <path
        d="M11 2.6 v2.2 M11 17.2 v2.2 M2.6 11 h2.2 M17.2 11 h2.2 M5.1 5.1 l1.6 1.6 M15.3 15.3 l1.6 1.6 M16.9 5.1 l-1.6 1.6 M6.7 15.3 l-1.6 1.6"
        {...base}
      />
    </Svg>
  );
}
