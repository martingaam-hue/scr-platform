import * as React from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "../lib/utils";

const sizeMap = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
  xl: "h-16 w-16 text-lg",
} as const;

export interface AvatarProps
  extends React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root> {
  src?: string | null;
  alt?: string;
  fallback?: string;
  size?: keyof typeof sizeMap;
}

function Avatar({
  src,
  alt,
  fallback,
  size = "md",
  className,
  ...props
}: AvatarProps) {
  const initials =
    fallback ||
    (alt
      ?.split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) ??
      "?");

  return (
    <AvatarPrimitive.Root
      className={cn(
        "relative flex shrink-0 overflow-hidden rounded-full",
        sizeMap[size],
        className
      )}
      {...props}
    >
      {src && (
        <AvatarPrimitive.Image
          className="aspect-square h-full w-full object-cover"
          src={src}
          alt={alt}
        />
      )}
      <AvatarPrimitive.Fallback className="flex h-full w-full items-center justify-center rounded-full bg-primary-100 font-medium text-primary-700 dark:bg-primary-900 dark:text-primary-300">
        {initials}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}

export interface AvatarGroupProps {
  avatars: Array<{ src?: string | null; alt?: string }>;
  max?: number;
  size?: keyof typeof sizeMap;
  className?: string;
}

function AvatarGroup({
  avatars,
  max = 4,
  size = "md",
  className,
}: AvatarGroupProps) {
  const visible = avatars.slice(0, max);
  const remaining = avatars.length - max;

  return (
    <div className={cn("flex -space-x-2", className)}>
      {visible.map((a, i) => (
        <Avatar
          key={i}
          src={a.src}
          alt={a.alt}
          size={size}
          className="ring-2 ring-white dark:ring-neutral-900"
        />
      ))}
      {remaining > 0 && (
        <span
          className={cn(
            "relative flex shrink-0 items-center justify-center rounded-full bg-neutral-200 font-medium text-neutral-600 ring-2 ring-white dark:bg-neutral-700 dark:text-neutral-300 dark:ring-neutral-900",
            sizeMap[size]
          )}
        >
          +{remaining}
        </span>
      )}
    </div>
  );
}

export { Avatar, AvatarGroup };
