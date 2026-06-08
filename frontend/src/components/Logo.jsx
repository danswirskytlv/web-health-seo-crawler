// The SitePulse pulse-wave + globe mark, inline SVG (no asset dependency).
export default function Logo({ size = 26 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: "block" }}
    >
      <circle cx="16" cy="16" r="13" stroke="var(--cyan)" strokeWidth="1.6" opacity="0.55" />
      <path
        d="M4 16 H10 L13 9 L19 23 L22 16 H28"
        stroke="var(--cyan)"
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// The "SitePulse" wordmark with 'Site' light and 'Pulse' cyan.
export function Wordmark() {
  return (
    <span className="wordmark">
      <span className="site">Site</span>
      <span className="pulse">Pulse</span>
    </span>
  );
}
