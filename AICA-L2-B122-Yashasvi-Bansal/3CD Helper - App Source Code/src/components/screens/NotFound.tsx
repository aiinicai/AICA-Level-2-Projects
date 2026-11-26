import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="text-6xl font-extrabold text-navy-900">404</div>
      <p className="mt-2 text-slate-500">This page doesn't exist.</p>
      <Link to="/" className="mt-6"><Button>Go home</Button></Link>
    </div>
  );
}
