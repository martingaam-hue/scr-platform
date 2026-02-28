import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (isPublicRoute(request)) {
    return;
  }

  // Protect all non-public routes
  const session = await auth.protect();

  // Role-based redirect for bare /dashboard
  if (request.nextUrl.pathname === "/dashboard") {
    // Custom session claims must be configured in Clerk dashboard
    const claims = session.sessionClaims as Record<string, unknown> | undefined;
    const orgType = claims?.org_type as string | undefined;

    if (orgType === "investor") {
      return NextResponse.redirect(new URL("/portfolio", request.url));
    }
    if (orgType === "ally") {
      return NextResponse.redirect(new URL("/projects", request.url));
    }
    // Default: stay on /dashboard
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
