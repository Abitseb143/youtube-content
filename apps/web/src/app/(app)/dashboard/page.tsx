import { auth } from "@clerk/nextjs/server";
import { UserButton } from "@clerk/nextjs";

export default async function DashboardPage() {
  const { userId } = await auth();

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <UserButton />
      </header>
      <p className="text-neutral-600">
        Signed in as <code className="text-sm">{userId}</code>.
      </p>
      <p className="mt-2 text-neutral-500">
        Connect a YouTube channel and create a content series to get started.
        (Coming in P4.)
      </p>
    </main>
  );
}
