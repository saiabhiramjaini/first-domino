"use client";

import { MenuIcon } from "lucide-react";
import { useState } from "react";

import { BrandName } from "@/components/brand/brand-name";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

import { AppNav } from "./app-nav";

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger render={<Button variant="ghost" size="icon" aria-label="Open navigation" />}>
        <MenuIcon />
      </SheetTrigger>
      <SheetContent side="left" className="w-72 p-4">
        <SheetHeader className="p-0 pb-4">
          <SheetTitle>
            <BrandName />
          </SheetTitle>
        </SheetHeader>
        <AppNav onNavigate={() => setIsOpen(false)} />
      </SheetContent>
    </Sheet>
  );
}
