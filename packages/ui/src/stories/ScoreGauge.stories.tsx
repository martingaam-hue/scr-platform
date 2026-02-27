import type { Meta, StoryObj } from "@storybook/react";
import { ScoreGauge } from "../components/score-gauge";

const meta: Meta<typeof ScoreGauge> = {
  title: "Components/ScoreGauge",
  component: ScoreGauge,
  argTypes: {
    score: { control: { type: "range", min: 0, max: 100, step: 1 } },
    size: { control: { type: "range", min: 80, max: 200, step: 10 } },
  },
};
export default meta;

export const High: StoryObj<typeof ScoreGauge> = {
  args: { score: 87, label: "Signal Score" },
};

export const Medium: StoryObj<typeof ScoreGauge> = {
  args: { score: 55, label: "ESG Rating" },
};

export const Low: StoryObj<typeof ScoreGauge> = {
  args: { score: 28, label: "Risk Score" },
};

export const AllRanges: StoryObj = {
  render: () => (
    <div className="flex items-end gap-8">
      <ScoreGauge score={15} size={100} label="Critical" />
      <ScoreGauge score={45} size={100} label="Below Avg" />
      <ScoreGauge score={68} size={100} label="Good" />
      <ScoreGauge score={92} size={100} label="Excellent" />
    </div>
  ),
};
