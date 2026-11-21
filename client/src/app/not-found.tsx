import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center gap-6 overflow-hidden p-4 text-center">
      <div className="relative flex flex-col items-center gap-6">
        <BrandName />
        <p className="font-mono text-sm text-muted-foreground">404</p>
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">This page fell over</h1>
          <p className="max-w-sm text-sm text-muted-foreground">
            The link may be old, or the record was removed.
          </p>
        </div>
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          Go home
        </Link>
      </div>
    </div>
  );
}
