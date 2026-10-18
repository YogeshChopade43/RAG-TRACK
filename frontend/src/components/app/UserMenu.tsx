import { useNavigate } from "react-router";
import { FileText, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";

/** Account menu. On small screens it also lists the document and model, which the top bar hides. */
export function UserMenu(props: { fileName?: string; modelLabel: string; onChangeDocument?(): void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initial = (user?.full_name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" aria-label="Account" className="rounded-full font-medium">
          {initial}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <div className="truncate text-sm font-medium">{user?.full_name || "Signed in"}</div>
          <div className="truncate text-xs text-muted-foreground">{user?.email}</div>
        </DropdownMenuLabel>
        <div className="grid gap-1 px-2 pb-1 text-xs text-muted-foreground sm:hidden">
          {props.fileName && <div className="truncate">Document: {props.fileName}</div>}
          <div className="truncate">Model: {props.modelLabel}</div>
        </div>
        <DropdownMenuSeparator />
        {props.onChangeDocument && (
          // The top bar's document chip (with its change button) is hidden on phones
          <DropdownMenuItem className="sm:hidden" onSelect={props.onChangeDocument}>
            <FileText aria-hidden />
            Change document
          </DropdownMenuItem>
        )}
        <DropdownMenuItem
          onSelect={async () => {
            await logout();
            navigate("/login", { replace: true });
          }}
        >
          <LogOut aria-hidden />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
