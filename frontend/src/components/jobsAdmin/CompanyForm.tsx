import { useState, type FormEvent } from 'react';
import { FieldError } from '@/components/auth/FieldError';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { isValidHttpUrl } from './validation';
import type { AdminCompany, CompanyInput } from '@/types/jobAdmin';

interface CompanyFormProps {
  company: AdminCompany | null;
  saving: boolean;
  onSubmit: (payload: CompanyInput) => void;
  onCancel: () => void;
}

export function CompanyForm({ company, saving, onSubmit, onCancel }: CompanyFormProps) {
  const [name, setName] = useState(company?.name ?? '');
  const [description, setDescription] = useState(company?.description ?? '');
  const [website, setWebsite] = useState(company?.website ?? '');
  const [nameError, setNameError] = useState<string | undefined>();
  const [websiteError, setWebsiteError] = useState<string | undefined>();

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const trimmedName = name.trim();
    const trimmedSite = website.trim();
    const nErr = trimmedName ? undefined : 'Company name is required.';
    const wErr = trimmedSite && !isValidHttpUrl(trimmedSite) ? 'Website must be a valid http:// or https:// URL.' : undefined;
    setNameError(nErr);
    setWebsiteError(wErr);
    if (nErr || wErr) return;
    onSubmit({ name: trimmedName, description: description.trim() || null, website: trimmedSite || null });
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="grid gap-4" aria-label="Company form">
      <div className="space-y-2">
        <Label htmlFor="company-name">Company name</Label>
        <Input id="company-name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={Boolean(nameError)} />
        <FieldError id="company-name-error" message={nameError} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="company-description">Description (optional)</Label>
        <Input id="company-description" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="company-website">Website (optional)</Label>
        <Input id="company-website" value={website} placeholder="https://example.com" onChange={(e) => setWebsite(e.target.value)} aria-invalid={Boolean(websiteError)} />
        <FieldError id="company-website-error" message={websiteError} />
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving...' : company ? 'Save company' : 'Create company'}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
