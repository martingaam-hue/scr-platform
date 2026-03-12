import { redirect } from "next/navigation";

// Redirect to renamed route
export default function DevelopmentOSRedirect() {
  redirect("/dev-tracker");
}
