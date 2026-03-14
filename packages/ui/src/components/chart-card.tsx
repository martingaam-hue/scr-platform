"use client";

import * as React from "react";
import { ResponsiveContainer } from "recharts";
import { cn } from "../lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "./card";

export interface ChartCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  height?: number;
  action?: React.ReactNode;
}

function ChartCard({ title, height = 300, action, children, className, ...props }: ChartCardProps) {
  return (
    <Card className={cn(className)} {...props}>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          {action}
        </CardHeader>
      )}
      <CardContent className={cn("p-6", title ? "pt-2" : "")}>
        <ResponsiveContainer width="100%" height={height}>
          {children as React.ReactElement}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export { ChartCard };
