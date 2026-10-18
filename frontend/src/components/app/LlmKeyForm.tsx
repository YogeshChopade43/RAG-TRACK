import { useId, useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import { FormAlert } from "@/components/AuthLayout";
import { PasswordInput } from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLlmSettings } from "@/hooks/useLlmSettings";
import { api } from "@/lib/api";

/**
 * Key + model form shared by onboarding and the Settings dialog.
 * The pair is saved only after OpenRouter accepts it.
 */
export function LlmKeyForm(props: { submitLabel: string; onVerified(): void }) {
  const settings = useLlmSettings();
  const id = useId();
  const [key, setKey] = useState(settings.apiKey);
  const [model, setModel] = useState(settings.model);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const result = await api.testApiKey(key.trim(), model.trim());
      if (!result.valid) {
        setError(result.message);
        return;
      }
      settings.saveVerified(key.trim(), model.trim());
      props.onVerified();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not test the key");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <FormAlert>{error}</FormAlert>
      <div className="grid gap-2">
        <Label htmlFor={`${id}-key`}>OpenRouter API key</Label>
        <PasswordInput
          id={`${id}-key`}
          placeholder="sk-or-..."
          autoComplete="off"
          spellCheck={false}
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${id}-model`}>Model</Label>
        <Input
          id={`${id}-model`}
          placeholder="openai/gpt-4o-mini"
          autoComplete="off"
          spellCheck={false}
          className="font-mono"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
      </div>
      <p className="text-sm text-muted-foreground">
        Kept only in this browser session. It pays for the chat model you choose and for a few small Jev
        decision calls per question (query checks, ranking passages, answer safety) — usually a fraction of a
        cent. Tip: use a separate OpenRouter key with a spending limit, so you can revoke it any time.
      </p>
      <Button type="submit" disabled={pending || !key.trim() || !model.trim()}>
        {pending && <Loader2 className="animate-spin" aria-hidden />}
        {props.submitLabel}
      </Button>
    </form>
  );
}
