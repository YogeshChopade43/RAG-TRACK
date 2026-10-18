import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { Loader2 } from "lucide-react";
import { AuthLayout, FieldError, FormAlert } from "@/components/AuthLayout";
import { PasswordInput } from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/useAuth";

type Errors = Partial<Record<"email" | "password" | "confirm", string>>;

function validate(email: string, password: string, confirm: string): Errors {
  const errors: Errors = {};
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = "Enter a valid email address";
  if (password.length < 8) errors.password = "Password must be at least 8 characters";
  if (confirm !== password) errors.confirm = "Passwords don't match";
  return errors;
}

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const found = validate(email.trim(), password, confirm);
    setErrors(found);
    if (Object.keys(found).length) return;

    setPending(true);
    try {
      await register(email.trim(), password, fullName.trim() || undefined);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setPending(false);
    }
  }

  const field = (key: keyof Errors) => ({
    "aria-invalid": errors[key] ? true : undefined,
    "aria-describedby": errors[key] ? `${key}-error` : undefined,
  });

  return (
    <AuthLayout
      title="Create account"
      description="Upload documents and see how every answer is made."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        <FormAlert>{error}</FormAlert>
        <div className="grid gap-2">
          <Label htmlFor="fullName">
            Full name <span className="text-muted-foreground">(optional)</span>
          </Label>
          <Input id="fullName" autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            {...field("email")}
          />
          <FieldError id="email-error">{errors.email}</FieldError>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="password">Password</Label>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            {...field("password")}
          />
          <FieldError id="password-error">{errors.password}</FieldError>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="confirm">Confirm password</Label>
          <PasswordInput
            id="confirm"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            {...field("confirm")}
          />
          <FieldError id="confirm-error">{errors.confirm}</FieldError>
        </div>
        <Button type="submit" disabled={pending}>
          {pending && <Loader2 className="animate-spin" aria-hidden />}
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
