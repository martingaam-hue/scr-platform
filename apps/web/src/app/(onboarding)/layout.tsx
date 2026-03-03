import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { OnboardingLayoutClient } from "./layout-client";

export default async function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }

  return <OnboardingLayoutClient>{children}</OnboardingLayoutClient>;
}
