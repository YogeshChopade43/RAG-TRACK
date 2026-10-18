import { useSyncExternalStore } from "react";
import { getVersion, subscribe, writeSession } from "@/lib/sessionStore";

/** OpenRouter key + model for this browser session; `verified` once the key passed a test. */
export function useLlmSettings() {
  useSyncExternalStore(subscribe, getVersion);
  return {
    apiKey: sessionStorage.getItem("llm_api_key") ?? "",
    model: sessionStorage.getItem("llm_model") ?? "",
    verified: sessionStorage.getItem("llm_verified") === "1",
    /** Store a key and model that just passed the test. */
    saveVerified(key: string, model: string) {
      writeSession({ llm_api_key: key, llm_model: model, llm_verified: "1" });
    },
    clear() {
      writeSession({ llm_api_key: null, llm_model: null, llm_verified: null });
    },
  };
}
