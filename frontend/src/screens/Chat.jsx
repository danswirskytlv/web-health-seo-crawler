import { useState, useRef, useEffect } from "react";
import PageHeader from "../components/PageHeader.jsx";
import { useScan } from "../state/ScanContext.jsx";
import { api } from "../api.js";

const SUGGESTIONS = [
  "What's the most urgent thing to fix?",
  "Why is my health score where it is?",
  "What is a meta description?",
  "Is my site mobile-friendly?",
];

export default function Chat() {
  const { scan } = useScan();
  const [messages, setMessages] = useState([]); // {role, content}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    const history = messages;
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setBusy(true);
    try {
      const reply = await api.aiChat(msg, history, scan?.scanId ?? null);
      setMessages((m) => [...m, { role: "assistant", content: reply.text }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Sorry — I couldn't reach the AI (" + e.message + ")." },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Ask Your Site"
        subtitle="Ask anything about your website's health and SEO, in plain language."
      />

      <div className="card" style={{ display: "flex", flexDirection: "column", height: "62vh", padding: 0 }}>
        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px" }}>
          {messages.length === 0 && (
            <div className="muted" style={{ textAlign: "center", marginTop: 24 }}>
              {scan
                ? `I can see your latest scan of ${scan.rootUrl}. Ask me anything about it.`
                : "Run a scan first for answers about your site — or ask a general SEO question."}
              <div className="flex gap-2 mt-3" style={{ flexWrap: "wrap", justifyContent: "center" }}>
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="badge" style={{ cursor: "pointer" }} onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <Bubble key={i} role={m.role}>{m.content}</Bubble>
          ))}
          {busy && (
            <Bubble role="assistant">
              <span className="flex items-center gap-2 muted"><span className="pulse-dot" /> Thinking…</span>
            </Bubble>
          )}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div style={{ borderTop: "1px solid var(--border)", padding: 14, display: "flex", gap: 10 }}>
          <input
            className="input"
            placeholder="Ask about your site's health or SEO…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn primary" onClick={() => send()} disabled={busy}>Send</button>
        </div>
      </div>
    </>
  );
}

function Bubble({ role, children }) {
  const isUser = role === "user";
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", marginBottom: 10 }}>
      <div
        style={{
          maxWidth: "76%",
          padding: "10px 14px",
          borderRadius: 14,
          lineHeight: 1.55,
          background: isUser ? "linear-gradient(180deg, var(--cyan), var(--blue))" : "var(--bg)",
          color: isUser ? "#04121a" : "var(--text)",
          border: isUser ? "none" : "1px solid var(--border)",
          whiteSpace: "pre-wrap",
        }}
      >
        {children}
      </div>
    </div>
  );
}
