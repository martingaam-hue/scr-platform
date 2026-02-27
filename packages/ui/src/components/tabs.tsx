"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex items-center gap-1 border-b border-neutral-200 dark:border-neutral-800",
      className
    )}
    {...props}
  />
));
TabsList.displayName = "TabsList";

export interface TabsTriggerProps
  extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> {
  badge?: number | string;
}

const TabsTrigger = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Trigger>,
  TabsTriggerProps
>(({ className, badge, children, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "relative inline-flex items-center gap-2 px-4 pb-3 pt-2 text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-900 data-[state=active]:text-primary-600 dark:text-neutral-400 dark:hover:text-neutral-100 dark:data-[state=active]:text-primary-400",
      "after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:rounded-full after:transition-colors data-[state=active]:after:bg-primary-600 dark:data-[state=active]:after:bg-primary-400",
      className
    )}
    {...props}
  >
    {children}
    {badge !== undefined && (
      <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-neutral-100 px-1.5 text-2xs font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
        {badge}
      </span>
    )}
  </TabsPrimitive.Trigger>
));
TabsTrigger.displayName = "TabsTrigger";

const TabsContent = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("mt-4 focus-visible:outline-none", className)}
    {...props}
  />
));
TabsContent.displayName = "TabsContent";

export { Tabs, TabsList, TabsTrigger, TabsContent };
