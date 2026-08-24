import type { ReactNode } from "react";

export function RightRail({ blocks }: { blocks: { title: string; body: ReactNode }[] }) {
  return (
    <aside
      className="hidden w-[300px] shrink-0 flex-col gap-5 border-l border-line p-5 xl:flex"
      aria-label="Bảng phụ"
    >
      {blocks.map((b) => (
        <section key={b.title}>
          <h2 className="mb-3 text-sm font-semibold">{b.title}</h2>
          {b.body}
        </section>
      ))}
    </aside>
  );
}
