import Link from "next/link";

export function Brand({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link
      href="/"
      onClick={onNavigate}
      className="flex items-center gap-2.5 font-mono"
      aria-label="PiScope home"
    >
      <span
        aria-hidden
        className="flex size-7 items-center justify-center border border-primary/60 bg-primary/10 text-base leading-none text-primary"
      >
        π
      </span>
      <span className="text-sm font-semibold tracking-wide">
        Pi<span className="text-cyan">Scope</span>
      </span>
    </Link>
  );
}
