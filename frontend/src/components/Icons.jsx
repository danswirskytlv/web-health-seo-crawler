// Shared thin-line SVG icon library (same style as the sidebar NavIcons):
// 22×22 viewBox, currentColor stroke at 1.6px, round caps/joins. Icons inherit
// the surrounding text color, so they pick up the cyan accent where used.
//
// Two groups:
//   CategoryIcon  — one per audit category (SEO, Accessibility, …)
//   UI icons      — buttons / metric cards / section headers

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

/* ======================= Category icons ======================= */

function SeoGlass() {
  return (
    <>
      <circle cx="9.5" cy="9.5" r="5.5" {...base} />
      <path d="M13.6 13.6 L18 18" {...base} />
    </>
  );
}
function A11y() {
  return (
    <>
      <circle cx="11" cy="4.4" r="1.4" {...base} />
      <path d="M4.5 7.5 C7 8.4 9 8.7 11 8.7 C13 8.7 15 8.4 17.5 7.5" {...base} />
      <path d="M11 8.7 V13" {...base} />
      <path d="M11 13 L8 18.5 M11 13 L14 18.5" {...base} />
    </>
  );
}
function Bolt() {
  return <path d="M12 2.5 L5 12 H10 L9 19.5 L16.5 9.5 H11.5 Z" {...base} />;
}
function Ruler() {
  return (
    <>
      <path d="M4 14.5 L14.5 4 L18 7.5 L7.5 18 Z" {...base} />
      <path d="M7 11.5 l1.6 1.6 M9.5 9 l1.6 1.6 M12 6.5 l1.6 1.6" {...base} />
    </>
  );
}
function Lock() {
  return (
    <>
      <rect x="5" y="9.5" width="12" height="9" rx="2" {...base} />
      <path d="M7.5 9.5 V7 a3.5 3.5 0 0 1 7 0 V9.5" {...base} />
      <circle cx="11" cy="13.6" r="1.1" fill="currentColor" stroke="none" />
    </>
  );
}
function Shield() {
  return (
    <>
      <path d="M11 2.5 L17.5 5 V10.5 C17.5 15 14.5 18 11 19.5 C7.5 18 4.5 15 4.5 10.5 V5 Z" {...base} />
      <path d="M8.3 10.8 L10.4 13 L14 8.6" {...base} />
    </>
  );
}
function Cookie() {
  return (
    <>
      <path d="M11 3.5 a7.5 7.5 0 1 0 7.4 8.6 a2.4 2.4 0 0 1 -2.9 -3 a2.4 2.4 0 0 1 -2.9 -3 a2.4 2.4 0 0 1 -1.6 -2.1 A7.5 7.5 0 0 0 11 3.5 Z" {...base} />
      <circle cx="8.5" cy="10" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="12.5" cy="13" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="9.5" cy="14.5" r="0.7" fill="currentColor" stroke="none" />
    </>
  );
}
function Megaphone() {
  return (
    <>
      <path d="M4 9 V13 L13 17 V5 Z" {...base} />
      <path d="M4 9 H6.5 V13 H4" {...base} />
      <path d="M13 8.5 C15 9 16 10 16 11 C16 12 15 13 13 13.5" {...base} />
      <path d="M6.5 13 V16.5 H8.5 V13.7" {...base} />
    </>
  );
}
function Eye() {
  return (
    <>
      <path d="M2.5 11 C4.5 7 7.5 5.5 11 5.5 C14.5 5.5 17.5 7 19.5 11 C17.5 15 14.5 16.5 11 16.5 C7.5 16.5 4.5 15 2.5 11 Z" {...base} />
      <circle cx="11" cy="11" r="2.6" {...base} />
    </>
  );
}

const CATEGORY_ICON = {
  SEO: SeoGlass,
  Accessibility: A11y,
  Performance: Bolt,
  Schema: Ruler,
  "Transport Security": Lock,
  "Security Headers": Shield,
  Cookies: Cookie,
  "Information Disclosure": Megaphone,
  Privacy: Eye,
  Security: Lock, // legacy
};

// Drop-in for an emoji category icon. Falls back to a small dot.
export function CategoryIcon({ name, size = 18 }) {
  const Glyph = CATEGORY_ICON[name];
  if (!Glyph) {
    return (
      <Svg size={size} label={name}>
        <circle cx="11" cy="11" r="2" fill="currentColor" stroke="none" />
      </Svg>
    );
  }
  return (
    <Svg size={size} label={name}>
      <Glyph />
    </Svg>
  );
}

/* ========================= UI icons ========================= */

export function SparkleIcon({ size = 16 }) {
  return (
    <Svg size={size} label="AI">
      <path d="M11 3 C11.6 6.6 12.4 7.4 16 8 C12.4 8.6 11.6 9.4 11 13 C10.4 9.4 9.6 8.6 6 8 C9.6 7.4 10.4 6.6 11 3 Z" {...base} />
      <path d="M16.5 13 C16.8 14.6 17.2 15 18.8 15.3 C17.2 15.6 16.8 16 16.5 17.6 C16.2 16 15.8 15.6 14.2 15.3 C15.8 15 16.2 14.6 16.5 13 Z" {...base} />
    </Svg>
  );
}

export function RobotIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Assistant">
      <rect x="4.5" y="7" width="13" height="9.5" rx="2.5" {...base} />
      <path d="M11 4 V7" {...base} />
      <circle cx="11" cy="3.4" r="1.1" {...base} />
      <circle cx="8.5" cy="11.2" r="1" fill="currentColor" stroke="none" />
      <circle cx="13.5" cy="11.2" r="1" fill="currentColor" stroke="none" />
      <path d="M9 14 H13" {...base} />
    </Svg>
  );
}

export function DocIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Document">
      <path d="M6 3 H13 L17 7 V19 H6 Z" {...base} />
      <path d="M13 3 V7 H17" {...base} />
      <path d="M8.5 11 H14 M8.5 14 H14 M8.5 16.5 H11.5" {...base} />
    </Svg>
  );
}

export function PdfIcon({ size = 18 }) {
  return (
    <Svg size={size} label="PDF">
      <path d="M6 3 H13 L17 7 V19 H6 Z" {...base} />
      <path d="M13 3 V7 H17" {...base} />
      <path d="M8 15.5 h6 M8 15.5 v-2 a1 1 0 0 1 1 -1 h0.6 a1 1 0 0 1 0 2 H8 M11.6 15.5 v-3 h1.4" {...base} />
    </Svg>
  );
}

export function ChartIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Chart">
      <path d="M3.5 3.5 V18.5 H18.5" {...base} />
      <path d="M7 14 V16.5 M11 10 V16.5 M15 6.5 V16.5" {...base} />
    </Svg>
  );
}

export function LinkIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Link">
      <path d="M9 13 a3.5 3.5 0 0 1 0 -5 L11.5 5.5 a3.5 3.5 0 0 1 5 5 L15 12" {...base} />
      <path d="M13 9 a3.5 3.5 0 0 1 0 5 L10.5 16.5 a3.5 3.5 0 0 1 -5 -5 L7 10" {...base} />
    </Svg>
  );
}

export function WarningIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Warning">
      <path d="M11 3.5 L19.5 18 H2.5 Z" {...base} />
      <path d="M11 9 V13" {...base} />
      <circle cx="11" cy="15.6" r="0.6" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function DotAlertIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Critical">
      <circle cx="11" cy="11" r="6.5" {...base} />
      <path d="M11 7.5 V11.5" {...base} />
      <circle cx="11" cy="14.3" r="0.7" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function NoteIcon({ size = 16 }) {
  return (
    <Svg size={size} label="Note">
      <path d="M5 3.5 H14 L17 6.5 V18.5 H5 Z" {...base} />
      <path d="M8 8.5 H14 M8 11 H14 M8 13.5 H12" {...base} />
    </Svg>
  );
}

export function CheckIcon({ size = 16 }) {
  return (
    <Svg size={size} label="Resolved">
      <circle cx="11" cy="11" r="7.5" {...base} />
      <path d="M7.7 11 L10 13.3 L14.3 8.5" {...base} />
    </Svg>
  );
}

export function ArrowRightIcon({ size = 14 }) {
  return (
    <Svg size={size} label="">
      <path d="M4 11 H17 M12.5 6.5 L17 11 L12.5 15.5" {...base} />
    </Svg>
  );
}

export function ArrowDownIcon({ size = 16 }) {
  return (
    <Svg size={size} label="Download">
      <path d="M11 3.5 V14 M6.5 9.5 L11 14 L15.5 9.5" {...base} />
      <path d="M4.5 18 H17.5" {...base} />
    </Svg>
  );
}

export function RadarIcon({ size = 18 }) {
  return (
    <Svg size={size} label="Scan">
      <path d="M11 11 L18 6" {...base} />
      <path d="M4.5 16.5a9 9 0 1 1 13 0" {...base} />
      <path d="M7.5 14a5 5 0 1 1 7 0" {...base} />
      <circle cx="11" cy="11" r="1.1" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function RetryIcon({ size = 14 }) {
  return (
    <Svg size={size} label="Retry">
      <path d="M17 6 a7.5 7.5 0 1 0 1.4 5" {...base} />
      <path d="M17.5 2.8 V6.2 H14" {...base} />
    </Svg>
  );
}

export function CelebrateIcon({ size = 18 }) {
  return (
    <Svg size={size} label="">
      <path d="M4 18 L8.5 7.5 L14.5 13.5 Z" {...base} />
      <path d="M14 4 V6 M17.5 5.5 L16 7 M18 9.5 H16" {...base} />
      <circle cx="12.5" cy="4.5" r="0.6" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function ClockIcon({ size = 16 }) {
  return (
    <Svg size={size} label="Response time">
      <circle cx="11" cy="11" r="7.5" {...base} />
      <path d="M11 6.5 V11 L14 12.8" {...base} />
    </Svg>
  );
}

export function ChatBubbleIcon({ size = 16 }) {
  return (
    <Svg size={size} label="Chat">
      <path d="M4 5.5 H18 a1.5 1.5 0 0 1 1.5 1.5 V14 a1.5 1.5 0 0 1 -1.5 1.5 H9 L5.5 18.5 V15.5 H4 a1.5 1.5 0 0 1 -1.5 -1.5 V7 A1.5 1.5 0 0 1 4 5.5 Z" {...base} />
      <path d="M7.5 9 H14.5 M7.5 12 H12" {...base} />
    </Svg>
  );
}

export function BulbIcon({ size = 18 }) {
  return (
    <Svg size={size} label="">
      <path d="M11 3.5 a5 5 0 0 1 3 9 V14 H8 V12.5 a5 5 0 0 1 3 -9 Z" {...base} />
      <path d="M8.5 16 H13.5 M9.3 18 H12.7" {...base} />
    </Svg>
  );
}
