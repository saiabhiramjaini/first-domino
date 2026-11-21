import { redirect } from "next/navigation";

// Failures are the Runs list filtered to failed runs; old links keep working.
export default function FailuresPage() {
  redirect("/runs?status=failed");
}
