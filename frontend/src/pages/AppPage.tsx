import { Dropzone } from "@/components/app/Dropzone";
import { ConnectStep, StepIndicator, type Step } from "@/components/app/Onboarding";
import { TopBar } from "@/components/app/TopBar";
import { ChatView } from "@/components/chat/ChatView";
import { useActiveDocument } from "@/hooks/useActiveDocument";
import { useLlmSettings } from "@/hooks/useLlmSettings";

export default function AppPage() {
  const { verified } = useLlmSettings();
  const { doc, set: setDoc } = useActiveDocument();
  const step: Step = !verified ? "connect" : !doc ? "upload" : "chat";

  return (
    <div className="flex min-h-dvh flex-col" data-testid="app-page">
      <TopBar fileName={doc?.fileName} onChangeDocument={doc ? () => setDoc(null) : undefined} />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-4 py-8 sm:px-6">
        {step !== "chat" && <StepIndicator current={step} />}
        {step === "connect" && <ConnectStep />}
        {step === "upload" && (
          <section data-testid="upload-step" aria-labelledby="upload-heading" className="grid gap-4">
            <h1 id="upload-heading" className="text-center text-lg font-semibold">
              Upload a document
            </h1>
            <Dropzone onUploaded={setDoc} />
          </section>
        )}
        {step === "chat" && doc && <ChatView documentId={doc.documentId} fileName={doc.fileName} />}
      </main>
    </div>
  );
}
