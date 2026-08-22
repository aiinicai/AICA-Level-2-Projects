import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/engagements")({
  component: () => <Outlet />,
});
