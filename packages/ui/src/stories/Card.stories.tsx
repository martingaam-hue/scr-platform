import type { Meta, StoryObj } from "@storybook/react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
  MetricCard,
} from "../components/card";
import { Button } from "../components/button";

const meta: Meta<typeof Card> = {
  title: "Components/Card",
  component: Card,
};
export default meta;

export const Default: StoryObj = {
  render: () => (
    <Card className="max-w-sm">
      <CardHeader>
        <CardTitle>Portfolio Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-neutral-600">Your portfolio contains 12 active investments across 4 sectors.</p>
      </CardContent>
      <CardFooter>
        <Button size="sm" variant="outline">View Details</Button>
      </CardFooter>
    </Card>
  ),
};

export const Hoverable: StoryObj = {
  render: () => (
    <Card hover className="max-w-sm">
      <CardContent>
        <p className="text-sm text-neutral-600">Hover over this card to see the effect.</p>
      </CardContent>
    </Card>
  ),
};

export const MetricCardUp: StoryObj<typeof MetricCard> = {
  render: () => (
    <div className="grid max-w-2xl grid-cols-3 gap-4">
      <MetricCard
        label="Total AUM"
        value="$42.8M"
        trend={{ direction: "up", value: "+12.3% YoY" }}
      />
      <MetricCard
        label="IRR"
        value="18.4%"
        trend={{ direction: "up", value: "+2.1pp" }}
      />
      <MetricCard
        label="Active Deals"
        value="24"
        trend={{ direction: "neutral", value: "No change" }}
      />
    </div>
  ),
};

export const MetricCardDown: StoryObj<typeof MetricCard> = {
  render: () => (
    <MetricCard
      label="Risk Score"
      value="67"
      trend={{ direction: "down", value: "-3.2pts" }}
      className="max-w-xs"
    />
  ),
};
