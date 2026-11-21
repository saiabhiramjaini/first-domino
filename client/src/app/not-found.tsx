import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 text-center">
      <h2 className="text-lg font-semibold">Page not found</h2>
      <p className="text-sm text-muted-foreground">
        The link may be old, or the record was removed.
      </p>
      <Link href="/" className={buttonVariants({ variant: "outline" })}>
        Go home
      </Link>
    </div>
  );
}
