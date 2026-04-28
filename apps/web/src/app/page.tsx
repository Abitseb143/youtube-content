import Link from "next/link";

export default function MarketingHome() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-24 text-center">
      <h1 className="text-5xl font-bold tracking-tight">Faceless YT</h1>
      <p className="mt-4 text-lg text-neutral-600">
        AI-generated faceless YouTube channel automation.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Link href="/sign-in" className="rounded bg-neutral-900 px-4 py-2 text-white">
          Sign in
        </Link>
        <Link href="/sign-up" className="rounded border border-neutral-300 px-4 py-2">
          Sign up
        </Link>
      </div>
    </main>
  );
}
