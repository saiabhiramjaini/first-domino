import { ApiKeys } from "./api-keys-card";
import { ProjectDetails } from "./project-details";
import { SetupSteps } from "./setup-steps";

type SectionProps = {
  id: string;
  title: string;
  description: string;
  children: React.ReactNode;
};

// A settings section: what it is on the left, the controls on the right. Stacks on a phone.
function Section({ id, title, description, children }: SectionProps) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="grid scroll-mt-20 gap-4 border-t py-8 first:border-t-0 first:pt-2 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10"
    >
      <div className="flex flex-col gap-1">
        <h2 id={`${id}-title`} className="text-sm font-medium">
          {title}
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">{description}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export function SettingsPage() {
  return (
    <div className="flex max-w-5xl flex-col">
      <Section
        id="connect"
        title="Connect your agent"
        description="Three steps. Each one ticks itself when First Domino sees it working."
      >
        <SetupSteps />
      </Section>
      <Section
        id="api-keys"
        title="API keys"
        description="Give each agent or machine its own key, so you can revoke one without touching the rest."
      >
        <ApiKeys />
      </Section>
      <Section
        id="project"
        title="Project"
        description="Details you may need when you set up the SDK."
      >
        <ProjectDetails />
      </Section>
    </div>
  );
}
