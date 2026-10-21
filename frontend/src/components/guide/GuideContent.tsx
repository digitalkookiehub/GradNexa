import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { slugify } from '@/lib/guide';

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  if (node && typeof node === 'object' && 'props' in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children);
  }
  return '';
}

type Props<T extends keyof JSX.IntrinsicElements> = ComponentPropsWithoutRef<T>;

// Raw HTML in the Markdown is not rendered (react-markdown default), so content cannot inject markup.
const components: Components = {
  h1: ({ children }: Props<'h1'>) => <h1 className="mb-4 text-3xl font-semibold">{children}</h1>,
  h2: ({ children }: Props<'h2'>) => (
    <h2 id={slugify(textOf(children))} className="mb-3 mt-10 scroll-mt-4 border-b pb-2 text-2xl font-semibold">
      {children}
    </h2>
  ),
  h3: ({ children }: Props<'h3'>) => <h3 className="mb-2 mt-6 text-lg font-semibold">{children}</h3>,
  p: ({ children }: Props<'p'>) => <p className="my-3 leading-7">{children}</p>,
  ul: ({ children }: Props<'ul'>) => <ul className="my-3 list-disc space-y-1 pl-6">{children}</ul>,
  ol: ({ children }: Props<'ol'>) => <ol className="my-3 list-decimal space-y-1 pl-6">{children}</ol>,
  blockquote: ({ children }: Props<'blockquote'>) => (
    <blockquote className="my-4 border-l-4 pl-4 text-muted-foreground">{children}</blockquote>
  ),
  hr: () => <hr className="my-8" />,
  a: ({ href, children }: Props<'a'>) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline">
      {children}
    </a>
  ),
  pre: ({ children }: Props<'pre'>) => (
    <pre className="my-4 overflow-x-auto rounded-md border bg-muted p-4 text-sm">{children}</pre>
  ),
  code: ({ className, children }: Props<'code'>) => (
    <code className={className ?? 'rounded bg-muted px-1 py-0.5 text-[0.9em]'}>{children}</code>
  ),
  table: ({ children }: Props<'table'>) => (
    <div className="my-4 overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">{children}</table>
    </div>
  ),
  th: ({ children }: Props<'th'>) => <th className="border bg-muted px-3 py-2 font-semibold">{children}</th>,
  td: ({ children }: Props<'td'>) => <td className="border px-3 py-2 align-top">{children}</td>,
};

export function GuideContent({ markdown }: { markdown: string }) {
  return (
    <article>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
