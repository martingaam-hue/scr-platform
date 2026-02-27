"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "../lib/utils";

export interface SearchInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  value?: string;
  onValueChange?: (value: string) => void;
  debounce?: number;
  shortcutHint?: string;
}

function SearchInput({
  value: controlledValue,
  onValueChange,
  debounce = 300,
  shortcutHint = "\u2318K",
  className,
  placeholder = "Search...",
  ...props
}: SearchInputProps) {
  const [internalValue, setInternalValue] = React.useState(
    controlledValue ?? ""
  );
  const timerRef = React.useRef<ReturnType<typeof setTimeout>>();

  React.useEffect(() => {
    if (controlledValue !== undefined) {
      setInternalValue(controlledValue);
    }
  }, [controlledValue]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInternalValue(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onValueChange?.(val);
    }, debounce);
  };

  const handleClear = () => {
    setInternalValue("");
    onValueChange?.("");
  };

  return (
    <div
      className={cn(
        "relative flex items-center rounded-md border border-neutral-200 bg-white transition-colors focus-within:border-primary-500 focus-within:ring-1 focus-within:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:focus-within:border-primary-400",
        className
      )}
    >
      <Search className="ml-3 h-4 w-4 shrink-0 text-neutral-400" />
      <input
        type="text"
        value={internalValue}
        onChange={handleChange}
        placeholder={placeholder}
        className="h-10 w-full bg-transparent px-3 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none dark:text-neutral-100"
        {...props}
      />
      {internalValue ? (
        <button
          type="button"
          onClick={handleClear}
          className="mr-2 rounded p-0.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
        >
          <X className="h-4 w-4" />
        </button>
      ) : (
        shortcutHint && (
          <kbd className="mr-3 hidden shrink-0 rounded border border-neutral-200 bg-neutral-50 px-1.5 py-0.5 text-2xs font-medium text-neutral-400 dark:border-neutral-700 dark:bg-neutral-800 sm:inline-flex">
            {shortcutHint}
          </kbd>
        )
      )}
    </div>
  );
}

export { SearchInput };
