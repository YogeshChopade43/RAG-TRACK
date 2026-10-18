import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Source } from "@/lib/types";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  traceId?: string;
  status: "pending" | "done" | "error";
  error?: string;
  /** For assistant messages: the question it answers (used by Retry). */
  question?: string;
};

let nextId = 0;
const newId = () => `m${++nextId}`;

/** Chat state for one document. Switching document starts a fresh conversation. */
export function useChat(documentId: string) {
  const [state, setState] = useState<{ documentId: string; messages: ChatMessage[] }>({
    documentId,
    messages: [],
  });
  // Synchronous guard: two asks in the same tick must not both send
  const pendingRef = useRef(false);
  const [pending, setPending] = useState(false);
  const docRef = useRef(documentId);

  // A new document resets the conversation (adjusting state during render)
  if (state.documentId !== documentId) {
    setState({ documentId, messages: [] });
    setPending(false);
  }
  useEffect(() => {
    docRef.current = documentId;
    pendingRef.current = false;
  }, [documentId]);

  const run = useCallback(
    async (assistantId: string, question: string) => {
      const askedFor = documentId;
      pendingRef.current = true;
      setPending(true);
      const update = (patch: Partial<ChatMessage>) => {
        // Drop answers for a document the user has since switched away from
        if (docRef.current !== askedFor) return;
        setState((s) => ({
          ...s,
          messages: s.messages.map((m) => (m.id === assistantId ? { ...m, ...patch } : m)),
        }));
      };
      try {
        const res = await api.query(askedFor, question);
        update({ status: "done", content: res.answer, sources: res.sources, traceId: res.trace_id });
      } catch (err) {
        update({ status: "error", error: err instanceof Error ? err.message : "Something went wrong" });
      } finally {
        if (docRef.current === askedFor) {
          pendingRef.current = false;
          setPending(false);
        }
      }
    },
    [documentId]
  );

  const ask = useCallback(
    (raw: string) => {
      const question = raw.trim();
      if (!question || pendingRef.current) return;
      pendingRef.current = true;
      const assistantId = newId();
      setState((s) => ({
        ...s,
        messages: [
          ...s.messages,
          { id: newId(), role: "user", content: question, sources: [], status: "done" },
          { id: assistantId, role: "assistant", content: "", sources: [], status: "pending", question },
        ],
      }));
      void run(assistantId, question);
    },
    [run]
  );

  const retry = useCallback(
    (messageId: string) => {
      const failed = state.messages.find((m) => m.id === messageId && m.status === "error");
      if (!failed?.question || pendingRef.current) return;
      setState((s) => ({
        ...s,
        messages: s.messages.map((m) => (m.id === messageId ? { ...m, status: "pending", error: undefined } : m)),
      }));
      return run(messageId, failed.question);
    },
    [state.messages, run]
  );

  return { messages: state.messages, pending, ask, retry };
}
