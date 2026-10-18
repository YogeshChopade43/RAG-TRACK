import { useSyncExternalStore } from "react";
import { getVersion, subscribe, writeSession } from "@/lib/sessionStore";

export type ActiveDocument = { documentId: string; fileName: string };

function read(): ActiveDocument | null {
  try {
    const doc = JSON.parse(sessionStorage.getItem("active_document") ?? "null");
    return doc && typeof doc.documentId === "string" ? doc : null;
  } catch {
    return null;
  }
}

/** The document being chatted about; survives a page reload within the session. */
export function useActiveDocument() {
  useSyncExternalStore(subscribe, getVersion);
  return {
    doc: read(),
    set(doc: ActiveDocument | null) {
      writeSession({ active_document: doc ? JSON.stringify(doc) : null });
    },
  };
}
