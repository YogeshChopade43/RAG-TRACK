import { useState } from "react";
import { FileText, Settings, X } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useLlmSettings } from "@/hooks/useLlmSettings";
import { cn } from "@/lib/utils";
import { SettingsDialog } from "./SettingsDialog";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";

export function TopBar(props: { fileName?: string; onChangeDocument?(): void }) {
  const { model, verified } = useLlmSettings();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const modelLabel = verified ? model : "Not connected";

  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4 sm:px-6">
        <Logo />
        {props.fileName && (
          <div className="hidden min-w-0 items-center gap-1 rounded-full border py-0.5 pr-1 pl-3 text-sm sm:flex">
            <FileText aria-hidden className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="max-w-56 truncate">{props.fileName}</span>
            {props.onChangeDocument && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-6 rounded-full"
                    aria-label="Change document"
                    onClick={props.onChangeDocument}
                  >
                    <X />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Change document</TooltipContent>
              </Tooltip>
            )}
          </div>
        )}
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <Button
            variant="outline"
            size="sm"
            className="hidden max-w-56 rounded-full font-mono text-xs sm:inline-flex"
            onClick={() => setSettingsOpen(true)}
          >
            <span
              aria-hidden
              className={cn("size-2 shrink-0 rounded-full", verified ? "bg-primary" : "bg-muted-foreground/50")}
            />
            <span className="truncate">{modelLabel}</span>
          </Button>
          <Button variant="ghost" size="icon" aria-label="Settings" onClick={() => setSettingsOpen(true)}>
            <Settings />
          </Button>
          <ThemeToggle />
          <UserMenu fileName={props.fileName} modelLabel={modelLabel} onChangeDocument={props.onChangeDocument} />
        </div>
      </div>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </header>
  );
}
