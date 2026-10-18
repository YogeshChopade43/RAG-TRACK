import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LlmKeyForm } from "./LlmKeyForm";

export function SettingsDialog(props: { open: boolean; onOpenChange(open: boolean): void }) {
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Model settings</DialogTitle>
          <DialogDescription>Change your OpenRouter key or model. A new key is saved once it passes the test.</DialogDescription>
        </DialogHeader>
        {/* Remount on open so the form starts from the saved values */}
        {props.open && (
          <LlmKeyForm
            submitLabel="Test & save"
            onVerified={() => {
              toast.success("Model settings saved");
              props.onOpenChange(false);
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
