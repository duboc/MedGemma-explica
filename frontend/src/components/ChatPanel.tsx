import { memo, useEffect, useRef, useState } from "react";
import type { AnalysisResult, ChatMessage } from "../types";
import { getStructureNames, getEducationalInfos } from "../types";
import { chatWithGemini, suggestQuestions } from "../hooks/useApi";
import { renderMarkdownToHtml } from "../utils/markdown";

interface Props {
  result: AnalysisResult;
  mockMode: boolean;
  onSave?: (messages: ChatMessage[]) => void;
}

const FALLBACK_QUESTIONS = [
  "What would this look like if the patient had pneumonia?",
  "How do I systematically read a chest X-ray?",
  "What are the most common pathologies affecting these structures?",
  "Can you quiz me on identifying this structure?",
  "What is the cardiothoracic ratio and is it normal here?",
];

const SUGGESTION_ICONS = [
  "\u{1F9EB}", // petri dish - pathology
  "\u{1F4CB}", // clipboard - systematic
  "\u{1FA7A}", // stethoscope - clinical
  "\u{1F9E0}", // brain - reasoning
  "\u{1F4CF}", // ruler - measurements
  "\u{1F4A1}", // lightbulb - insight
];

/** Memoized chat message bubble — only re-renders when content changes. */
const ChatBubble = memo(function ChatBubble({
  role,
  content,
}: {
  role: "user" | "assistant";
  content: string;
}) {
  return (
    <div className={`chat-message chat-message--${role}`}>
      <div className="chat-message-label">
        {role === "user" ? "You" : "MedGemma"}
      </div>
      {role === "assistant" ? (
        <div
          className="chat-message-content"
          dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(content) }}
        />
      ) : (
        <div className="chat-message-content">{content}</div>
      )}
    </div>
  );
});

export default function ChatPanel({ result, mockMode, onSave }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(result.chat_messages ?? []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_QUESTIONS);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const structureNames = getStructureNames(result);
  const eduInfos = getEducationalInfos(result);

  // Fetch dynamic suggestions from MedGemma when the panel loads
  useEffect(() => {
    let cancelled = false;
    setLoadingSuggestions(true);
    suggestQuestions(structureNames, eduInfos, mockMode, result.image_url)
      .then((data) => {
        if (!cancelled && data?.questions?.length > 0) {
          setSuggestions(data.questions);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingSuggestions(false);
      });
    return () => { cancelled = true; };
  }, [result.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInput("");
    setLoading(true);

    try {
      const res = await chatWithGemini(updated, structureNames, eduInfos, mockMode, result.image_url);
      const withResponse = [...updated, { role: "assistant" as const, content: res.response }];
      setMessages(withResponse);
      onSave?.(withResponse);
    } catch {
      const withError = [
        ...updated,
        { role: "assistant" as const, content: "Sorry, I couldn't process that question. Please try again." },
      ];
      setMessages(withError);
      onSave?.(withError);
    } finally {
      setLoading(false);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>Ask About This X-ray</h3>
        <span className="rv-badge">MedGemma Q&A</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask questions about the structures, findings, or related pathology.</p>
            {loadingSuggestions ? (
              <div className="chat-suggestions-loading">
                <span className="spinner" /> Generating questions for this X-ray...
              </div>
            ) : (
              <div className="chat-suggestions-grid">
                {suggestions.slice(0, 6).map((q, i) => (
                  <button
                    key={i}
                    className="chat-suggestion-card"
                    onClick={() => sendMessage(q)}
                  >
                    <span className="chat-suggestion-icon">{SUGGESTION_ICONS[i % SUGGESTION_ICONS.length]}</span>
                    <span className="chat-suggestion-text">{q}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content} />
        ))}

        {loading && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message-label">MedGemma</div>
            <div className="chat-message-content chat-typing">
              <span className="spinner" /> Thinking...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about the X-ray findings..."
          disabled={loading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </form>
    </div>
  );
}
