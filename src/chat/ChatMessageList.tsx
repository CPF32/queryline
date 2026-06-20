import { useEffect, useRef } from "react";
import QueryResultPanel from "@/chat/QueryResultPanel";
import type { ChatMessage } from "@/chat/types";

export interface ChatMessageListProps {
  messages: ChatMessage[];
  dataSourceName?: string;
}

export default function ChatMessageList({
  messages,
  dataSourceName = "your data source",
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-message-list chat-message-list--empty">
        <div className="chat-empty-state">
          <h2>What do you want to know?</h2>
          <p>Ask anything about {dataSourceName}.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-message-list">
      {messages.map((message) => (
        <article
          key={message.id}
          className={`chat-message chat-message--${message.role}`}
        >
          <div className="chat-message__bubble">
            {message.role === "user" ? (
              <p>{message.content}</p>
            ) : (
              <QueryResultPanel message={message} />
            )}
          </div>
        </article>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
