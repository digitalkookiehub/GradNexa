import { Link } from 'react-router-dom';

interface BrandProps {
  showTagline?: boolean;
}

export const TAGLINE = 'From Engineering Graduate to Industry-Ready Professional.';

export function Brand({ showTagline = false }: BrandProps) {
  return (
    <div className="flex flex-col items-center gap-1 text-center">
      <Link to="/" className="text-2xl font-bold tracking-tight text-primary">
        GradNexa
      </Link>
      {showTagline && <p className="text-sm text-muted-foreground">{TAGLINE}</p>}
    </div>
  );
}
