import type { Meta, StoryObj } from "@storybook/react";
import {
  Drawer,
  DrawerTrigger,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerBody,
  DrawerFooter,
} from "../components/drawer";
import { Button } from "../components/button";

const meta: Meta<typeof Drawer> = {
  title: "Components/Drawer",
  component: Drawer,
};
export default meta;

export const Right: StoryObj = {
  render: () => (
    <Drawer>
      <DrawerTrigger asChild>
        <Button>Open Drawer</Button>
      </DrawerTrigger>
      <DrawerContent side="right">
        <DrawerHeader>
          <DrawerTitle>Project Details</DrawerTitle>
        </DrawerHeader>
        <DrawerBody>
          <div className="space-y-4 text-sm text-neutral-600">
            <p>Project Name: Solar Farm Alpha</p>
            <p>Status: Active</p>
            <p>Location: Arizona, US</p>
            <p>Capacity: 50MW</p>
          </div>
        </DrawerBody>
        <DrawerFooter>
          <Button variant="outline">Close</Button>
          <Button>Edit Project</Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  ),
};
