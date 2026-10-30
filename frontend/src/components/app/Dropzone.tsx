import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { AlertCircle, FileUp, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { ActiveDocument } from "@/hooks/useActiveDocument";
import { api } from "@/lib/api";
import type { IngestStage } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = ["pdf", "txt", "docx", "pptx", "html"];
const STAGES: Partial<Record<IngestStage, string>> = {
  queued: "Waiting for another upload to finish…",
  parsing: "Reading pages (OCR where needed)…",
  chunking: "Splitting into chunks…",
  embedding: "Embedding…",
};
const MAX_POLL_ERRORS = 5;
const LOST_CONTACT = "Lost contact with the server while processing. Please try again.";

function validate(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!ALLOWED.includes(ext)) return "Only PDF, Word, PowerPoint, HTML or TXT files can be uploaded.";
  if (file.size > MAX_BYTES) return "File is larger than 10 MB.";
  return null;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function Dropzone({ onUploaded, pollMs = 1000 }: { onUploaded(doc: ActiveDocument): void; pollMs?: number }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const alive = useRef(true);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stage, setStage] = useState<IngestStage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedFile, setFailedFile] = useState<File | null>(null);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  /** Poll the background ingestion until the document is ready (or fails). */
  async function waitUntilReady(documentId: string): Promise<boolean> {
    let errors = 0;
    for (;;) {
      await sleep(pollMs);
      if (!alive.current) return false;
      let s;
      try {
        s = await api.getIngestStatus(documentId);
        errors = 0;
      } catch {
        if (++errors >= MAX_POLL_ERRORS) throw new Error(LOST_CONTACT);
        continue;
      }
      if (s.status === "ready") return true;
      if (s.status === "failed") throw new Error(s.error ?? "Failed to process document");
      setStage(s.status);
    }
  }

  async function upload(file: File) {
    const invalid = validate(file);
    if (invalid) {
      setError(invalid);
      setFailedFile(null);
      return;
    }
    setError(null);
    setFailedFile(null);
    setStage(null);
    setUploading(true);
    try {
      const res = await api.uploadDocument(file);
      if (await waitUntilReady(res.document_id)) onUploaded({ documentId: res.document_id, fileName: res.filename });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setFailedFile(file);
    } finally {
      setUploading(false);
    }
  }

  function openPicker() {
    if (!uploading) inputRef.current?.click();
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPicker();
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && !uploading) void upload(file);
  }

  return (
    <div className="mx-auto grid w-full max-w-lg gap-3">
      <div
        role="button"
        tabIndex={uploading ? -1 : 0}
        aria-label="Upload a document: choose a file or drag it here"
        aria-disabled={uploading}
        // input.click() bubbles back up here; ignore it or the picker opens twice
        onClick={(e) => e.target !== inputRef.current && openPicker()}
        onKeyDown={onKeyDown}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "grid cursor-pointer place-items-center gap-3 rounded-xl border-2 border-dashed border-ink bg-card px-6 py-12 text-center transition-[background-color,box-shadow]",
          "hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          dragging && "border-solid bg-accent shadow-[5px_5px_0_var(--ink)]",
          uploading && "cursor-default",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.docx,.pptx,.html"
          aria-label="Choose a file"
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = ""; // allow picking the same file again
            if (file) void upload(file);
          }}
        />
        <span
          aria-hidden
          className="grid size-12 place-items-center rounded-lg border-2 border-ink bg-primary text-primary-foreground shadow-[2px_2px_0_var(--ink)]"
        >
          <FileUp className="size-6" />
        </span>
        {uploading ? (
          <div className="grid w-full max-w-xs gap-2" aria-live="polite">
            <p className="font-medium">Processing document</p>
            <Progress value={null} aria-label="Processing document" className="h-1.5 overflow-hidden" />
            <p className="font-mono text-xs text-muted-foreground">{(stage && STAGES[stage]) ?? "Uploading…"}</p>
          </div>
        ) : (
          <>
            <p className="font-heading font-semibold">
              Drop a document here or <span className="text-highlight underline-offset-4">choose a file</span>
            </p>
            <p className="text-sm text-muted-foreground">PDF, Word, PowerPoint, HTML or TXT · max 10 MB</p>
          </>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          <AlertCircle aria-hidden className="mt-0.5 size-4 shrink-0" />
          <p className="flex-1">{error}</p>
          {failedFile && (
            <Button size="sm" variant="outline" onClick={() => void upload(failedFile)}>
              <RotateCcw aria-hidden />
              Try again
            </Button>
          )}
        </div>
      )}

      <p className="text-center text-xs text-muted-foreground">
        Privacy: to answer questions, parts of your document's text are sent to OpenRouter (the chat model you choose)
        and TypeSafe (Jev decision model). Don't upload documents you can't share with them. Question traces, which
        include document text, are stored on this server for a retention period set by the operator.
      </p>
    </div>
  );
}
