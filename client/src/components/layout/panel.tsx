import { cn } from "@/lib/utils";

type PanelProps = {
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  id?: string;
  "aria-labelledby"?: string;
};

// A bordered surface with an optional header row. Lists and tables sit flush inside it.
export function Panel({
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
  id,
}: PanelProps) {
  const headingId = id ? `${id}-title` : undefined;
  return (
    <section
      id={id}
      aria-labelledby={title ? headingId : undefined}
      className={cn("flex min-w-0 flex-col rounded-lg border", className)}
    >
      {(title || actions) && (
        <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5">
          <div className="flex min-w-0 flex-col gap-0.5">
            {title && (
              <h2 id={headingId} className="text-sm font-medium">
                {title}
              </h2>
            )}
            {description && <p className="text-xs text-muted-foreground">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={cn("min-w-0", bodyClassName)}>{children}</div>
    </section>
  );
}
