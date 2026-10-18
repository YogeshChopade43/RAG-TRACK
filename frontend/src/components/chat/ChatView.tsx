import { TracePanel } from "@/components/trace/TracePanel";
import { useChat } from "@/hooks/useChat";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import { MessageList } from "./MessageList";

const renderTrace = (traceId: string) => <TracePanel traceId={traceId} />;

export function ChatView(props: { documentId: string; fileName: string }) {
  const { messages, pending, ask, retry } = useChat(props.documentId);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6">
      <div className="flex-1">
        {messages.length === 0 ? (
          <EmptyState fileName={props.fileName} onPick={ask} />
        ) : (
          <MessageList messages={messages} onRetry={retry} renderTrace={renderTrace} />
        )}
      </div>
      <div className="sticky bottom-0 bg-background pb-4">
        <Composer disabled={pending} onSend={ask} />
      </div>
    </div>
  );
}
