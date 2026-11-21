import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
};

export function EmptyState({ title, description, action, icon: Icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      {Icon && (
        <span className="flex size-9 items-center justify-center rounded-lg border text-muted-foreground">
          <Icon className="size-4" aria-hidden="true" />
        </span>
      )}
      <div className="flex flex-col gap-1">
        <p className="font-medium">{title}</p>
        <p className="max-w-md text-sm text-pretty text-muted-foreground">{description}</p>
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
}
