import { ProjectDetails } from "./project-details";
import { SetupProgress, SetupSteps } from "./setup-steps";

type SectionProps = {
  id: string;
  title: string;
  description: string;
  meta?: React.ReactNode;
  children: React.ReactNode;
};

// A section: its title and one line on top, then its card.
function Section({ id, title, description, meta, children }: SectionProps) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="flex min-w-0 scroll-mt-8 flex-col gap-3"
    >
      <div className="flex min-h-10 items-end justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h2 id={`${id}-title`} className="text-base font-semibold tracking-tight">
            {title}
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">{description}</p>
        </div>
        {meta}
      </div>
      {children}
    </section>
  );
}

// Setup takes the main column; the project's details sit beside it on wide screens and below
// it on narrow ones.
export function SettingsPage() {
  return (
    <div className="grid w-full items-start gap-10 xl:grid-cols-[minmax(0,1fr)_20rem] xl:gap-8">
      <Section
        id="connect"
        title="Connect your agent"
        description="Three steps. Each one ticks itself when First Domino sees it working."
        meta={<SetupProgress />}
      >
        <SetupSteps />
      </Section>
      <Section id="project" title="Project" description="Details you may need when setting up.">
        <ProjectDetails />
      </Section>
    </div>
  );
}
