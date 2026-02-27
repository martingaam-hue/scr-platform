import type { Meta, StoryObj } from "@storybook/react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/tabs";

const meta: Meta<typeof Tabs> = {
  title: "Components/Tabs",
  component: Tabs,
};
export default meta;

export const Default: StoryObj = {
  render: () => (
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="financials" badge={3}>Financials</TabsTrigger>
        <TabsTrigger value="documents" badge={12}>Documents</TabsTrigger>
        <TabsTrigger value="activity">Activity</TabsTrigger>
      </TabsList>
      <TabsContent value="overview">
        <p className="text-sm text-neutral-600">Overview content goes here.</p>
      </TabsContent>
      <TabsContent value="financials">
        <p className="text-sm text-neutral-600">Financial data and charts.</p>
      </TabsContent>
      <TabsContent value="documents">
        <p className="text-sm text-neutral-600">Document list.</p>
      </TabsContent>
      <TabsContent value="activity">
        <p className="text-sm text-neutral-600">Activity feed.</p>
      </TabsContent>
    </Tabs>
  ),
};
