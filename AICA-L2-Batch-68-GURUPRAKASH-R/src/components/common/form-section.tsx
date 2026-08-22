import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface FormSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  columns?: 1 | 2;
}

export function FormSection({
  title,
  description,
  children,
  className,
  columns = 2,
}: FormSectionProps) {
  return (
    <section className={cn("border-b border-border py-6 last:border-b-0", className)}>
      <div className="grid gap-5 lg:grid-cols-[240px_1fr]">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
        </div>
        <div className={cn("grid gap-4", columns === 2 && "sm:grid-cols-2")}>{children}</div>
      </div>
    </section>
  );
}
