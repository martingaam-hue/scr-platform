import * as React from "react";
import { cn } from "../lib/utils";
import { Card, CardContent } from "./card";
import { StatCard, type StatCardProps } from "./stat-card";

export interface HeroStatItem extends Omit<StatCardProps, "className"> {
  key?: string;
}

export interface HeroStatsRowProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Large element shown on the left (e.g. ScoreGauge) */
  hero: React.ReactNode;
  stats: HeroStatItem[];
}

function HeroStatsRow({ hero, stats, className, ...props }: HeroStatsRowProps) {
  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row", className)} {...props}>
      <div className="flex shrink-0 items-center justify-center sm:w-40">{hero}</div>
      <div className="grid flex-1 grid-cols-2 gap-3">
        {stats.map((stat, i) => {
          const { key, ...statProps } = stat;
          return (
            <Card key={key ?? i} hover>
              <CardContent className="p-4">
                <StatCard {...statProps} />
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export { HeroStatsRow };
