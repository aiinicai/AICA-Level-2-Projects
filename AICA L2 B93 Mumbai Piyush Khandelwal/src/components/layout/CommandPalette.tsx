import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { NAV } from "./nav";
import { useWorkspace } from "@/lib/store";
import { listDatasets } from "@/lib/query/engine";
import { INTEGRATIONS } from "@/lib/integrations/catalog";
import { CUSTOMERS } from "@/lib/data/demo-source";
import { Sparkles } from "lucide-react";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssistant: () => void;
}

export function CommandPalette({ open, onOpenChange, onAssistant }: Props) {
  const navigate = useNavigate();
  const { dashboards, reports, connections } = useWorkspace();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const go = (to: string) => {
    onOpenChange(false);
    navigate({ to: to as never });
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search dashboards, datasets, customers, integrations…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Assistant">
          <CommandItem
            onSelect={() => {
              onOpenChange(false);
              onAssistant();
            }}
          >
            <Sparkles className="size-4 text-primary" aria-hidden />
            Ask your data
          </CommandItem>
        </CommandGroup>

        <CommandGroup heading="Navigate">
          {NAV.map((item) => (
            <CommandItem key={item.to} onSelect={() => go(item.to)}>
              <item.icon className="size-4" aria-hidden />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />
        <CommandGroup heading="Dashboards">
          {dashboards.map((d) => (
            <CommandItem key={d.id} onSelect={() => go(`/dashboards/${d.id}`)}>
              {d.name}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading="Reports">
          {reports.map((r) => (
            <CommandItem key={r.id} onSelect={() => go(`/reports/${r.id}`)}>
              {r.name}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading="Datasets">
          {listDatasets().map((d) => (
            <CommandItem key={d.id} onSelect={() => go("/explorer")}>
              {d.name}
              <span className="ml-auto text-xs text-muted-foreground">{d.recordCount.toLocaleString("en-IN")} rows</span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading="Customers">
          {CUSTOMERS.slice(0, 8).map((c) => (
            <CommandItem key={c} onSelect={() => go("/explorer")}>
              {c}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandGroup heading="Integrations">
          {INTEGRATIONS.slice(0, 8).map((i) => (
            <CommandItem key={i.id} onSelect={() => go("/integrations")}>
              {i.name}
              <span className="ml-auto text-xs text-muted-foreground">
                {connections.some((c) => c.providerId === i.id) ? "Connected" : i.category}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
