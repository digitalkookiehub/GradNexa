import { useState, type KeyboardEvent } from 'react';
import { mergeTags } from '@/lib/tags';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface TagInputProps {
  id: string;
  label: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  disabled?: boolean;
}

export function TagInput({ id, label, tags, onChange, disabled }: TagInputProps) {
  const [draft, setDraft] = useState('');

  const commit = (): void => {
    if (draft.trim()) onChange(mergeTags(tags, draft));
    setDraft('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Backspace' && draft === '' && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {tags.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label={`${label} list`}>
          {tags.map((tag) => (
            <li key={tag} className="flex items-center gap-1 rounded-full bg-secondary px-3 py-1 text-xs">
              {tag}
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground"
                aria-label={`Remove ${tag}`}
                onClick={() => onChange(tags.filter((t) => t !== tag))}
                disabled={disabled}
              >
                x
              </button>
            </li>
          ))}
        </ul>
      )}
      <Input
        id={id}
        value={draft}
        placeholder="Type a skill and press Enter or comma"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commit}
        disabled={disabled}
      />
    </div>
  );
}
