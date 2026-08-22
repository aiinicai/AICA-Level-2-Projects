import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface RowAction {
  label: string;
  onSelect?: () => void;
  disabled?: boolean;
  hidden?: boolean;
  /** Renders a separator above this item. */
  divider?: boolean;
  title?: string;
}

/** Compact per-row action menu shared by the Stage 3 registers. */
export function RowActions({ actions, label = "Record actions" }: { actions: RowAction[]; label?: string }) {
  const visible = actions.filter((action) => !action.hidden);
  if (visible.length === 0) return null;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 px-2" aria-label={label}>
          <MoreHorizontal className="size-4" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {visible.map((action, index) => (
          <div key={action.label}>
            {action.divider && index > 0 && <DropdownMenuSeparator />}
            <DropdownMenuItem
              disabled={action.disabled}
              title={action.title}
              onSelect={(event) => {
                event.preventDefault();
                action.onSelect?.();
              }}
            >
              {action.label}
            </DropdownMenuItem>
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
