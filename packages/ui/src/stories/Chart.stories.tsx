import type { Meta, StoryObj } from "@storybook/react";
import { LineChart, BarChart, AreaChart, DonutChart } from "../components/chart";

const meta: Meta = {
  title: "Components/Chart",
};
export default meta;

const timeSeriesData = [
  { month: "Jan", irr: 12.1, nav: 41.2 },
  { month: "Feb", irr: 12.8, nav: 42.0 },
  { month: "Mar", irr: 13.2, nav: 41.8 },
  { month: "Apr", irr: 14.1, nav: 43.5 },
  { month: "May", irr: 15.4, nav: 44.2 },
  { month: "Jun", irr: 16.0, nav: 45.1 },
  { month: "Jul", irr: 15.8, nav: 44.8 },
  { month: "Aug", irr: 16.5, nav: 46.3 },
  { month: "Sep", irr: 17.2, nav: 47.0 },
  { month: "Oct", irr: 17.8, nav: 48.2 },
  { month: "Nov", irr: 18.1, nav: 49.0 },
  { month: "Dec", irr: 18.4, nav: 50.5 },
];

const barData = [
  { sector: "Solar", value: 35 },
  { sector: "Wind", value: 25 },
  { sector: "EV", value: 15 },
  { sector: "H2", value: 10 },
  { sector: "Nature", value: 15 },
];

const donutData = [
  { name: "Solar", value: 35 },
  { name: "Wind", value: 25 },
  { name: "Transport", value: 15 },
  { name: "Hydrogen", value: 10 },
  { name: "Nature-based", value: 15 },
];

const cashFlowData = [
  { quarter: "Q1 '24", inflow: 5.2, outflow: 3.1 },
  { quarter: "Q2 '24", inflow: 6.8, outflow: 4.2 },
  { quarter: "Q3 '24", inflow: 7.5, outflow: 3.8 },
  { quarter: "Q4 '24", inflow: 8.1, outflow: 5.0 },
];

export const LineChartStory: StoryObj = {
  name: "Line Chart — Time Series",
  render: () => (
    <LineChart
      data={timeSeriesData}
      xKey="month"
      yKeys={["irr", "nav"]}
      yLabels={{ irr: "IRR (%)", nav: "NAV ($M)" }}
      height={350}
    />
  ),
};

export const BarChartStory: StoryObj = {
  name: "Bar Chart — Allocation",
  render: () => (
    <BarChart
      data={barData}
      xKey="sector"
      yKeys={["value"]}
      yLabels={{ value: "Allocation (%)" }}
      height={300}
    />
  ),
};

export const AreaChartStory: StoryObj = {
  name: "Area Chart — Cash Flows",
  render: () => (
    <AreaChart
      data={cashFlowData}
      xKey="quarter"
      yKeys={["inflow", "outflow"]}
      yLabels={{ inflow: "Inflows ($M)", outflow: "Outflows ($M)" }}
      stacked
      height={300}
    />
  ),
};

export const DonutChartStory: StoryObj = {
  name: "Donut Chart — Sector Split",
  render: () => (
    <DonutChart
      data={donutData}
      nameKey="name"
      valueKey="value"
      height={300}
    />
  ),
};
