import { useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function Composer(props: { disabled: boolean; onSend(text: string): void }) {
  const [text, setText] = useState("");
  const canSend = !props.disabled && text.trim().length > 0;

  function send() {
    if (!canSend) return;
    props.onSend(text);
    setText("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter (and IME composition) inserts a newline
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  }

  return (
    <form
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        send();
      }}
      className="flex items-end gap-2 rounded-xl border-2 border-ink bg-card p-2 shadow-[3px_3px_0_var(--ink)] transition-shadow focus-within:shadow-[5px_5px_0_var(--ink)]"
    >
      <Textarea
        aria-label="Ask about this document"
        placeholder="Ask about this document…"
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        className="max-h-40 min-h-9 resize-none border-0 bg-transparent shadow-none focus-visible:shadow-none focus-visible:ring-0"
      />
      <Button type="submit" size="icon" aria-label="Send" disabled={!canSend} className="shrink-0">
        <ArrowUp />
      </Button>
    </form>
  );
}
