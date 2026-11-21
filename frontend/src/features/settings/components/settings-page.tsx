import { ApiKeysCard } from "./api-keys-card";
import { ConnectAgentCard } from "./connect-agent-card";
import { ProjectCard } from "./project-card";
import { SlackWebhookCard } from "./slack-webhook-card";

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <ProjectCard />
      <ConnectAgentCard />
      <ApiKeysCard />
      <SlackWebhookCard />
    </div>
  );
}
