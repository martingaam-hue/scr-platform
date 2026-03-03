import { OnboardingLayoutClient } from "./layout-client";

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <OnboardingLayoutClient>{children}</OnboardingLayoutClient>;
}
