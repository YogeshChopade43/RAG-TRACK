import { useEffect, useRef, type ReactNode } from "react";
import type { ChatMessage } from "@/hooks/useChat";
import { Message } from "./Message";

/** Scrolls to the newest message unless the user has scrolled up to read. */
export function MessageList(props: {
  messages: ChatMessage[];
  onRetry(id: string): void;
  renderTrace?: (traceId: string) => ReactNode;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const last = props.messages.at(-1);

  useEffect(() => {
    const nearBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 200;
    if (nearBottom) endRef.current?.scrollIntoView?.({ block: "end", behavior: "smooth" });
  }, [last?.id, last?.status]);

  return (
    <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-col gap-4">
      {props.messages.map((m) => (
        <Message key={m.id} message={m} onRetry={props.onRetry} renderTrace={props.renderTrace} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
