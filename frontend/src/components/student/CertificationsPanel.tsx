import { useEffect, useState, type FormEvent } from 'react';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { validateCertification, type FieldErrors } from '@/lib/studentValidation';
import { studentService } from '@/services/studentService';
import type { Certification } from '@/types';

export function CertificationsPanel() {
  const [items, setItems] = useState<Certification[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [issuer, setIssuer] = useState('');
  const [issuedOn, setIssuedOn] = useState('');
  const [errors, setErrors] = useState<FieldErrors<'name' | 'issued_on'>>({});
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    studentService
      .listCertifications()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setListError(getErrorMessage(err, 'Could not load certifications.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setListError(null);
    const found = validateCertification(name, issuedOn);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSubmitting(true);
    try {
      const created = await studentService.createCertification({
        name: name.trim(),
        issuer: issuer.trim() || null,
        issued_on: issuedOn || null,
      });
      setItems((prev) => [...prev, created]);
      setName('');
      setIssuer('');
      setIssuedOn('');
    } catch (err) {
      setListError(getErrorMessage(err, 'Could not add the certification.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number): Promise<void> => {
    setListError(null);
    setDeletingId(id);
    try {
      await studentService.deleteCertification(id);
      setItems((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setListError(getErrorMessage(err, 'Could not delete the certification.'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <FormMessage message={listError} />
      {loading ? (
        <p role="status" className="text-sm text-muted-foreground">
          Loading certifications...
        </p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No certifications yet.</p>
      ) : (
        <ul className="space-y-3" aria-label="Certifications">
          {items.map((c) => (
            <li key={c.id} className="flex items-start justify-between gap-4 rounded-md border p-4 text-sm">
              <div>
                <div className="font-medium">{c.name}</div>
                <div className="text-muted-foreground">
                  {[c.issuer, c.issued_on].filter((v): v is string => Boolean(v)).join(' | ')}
                </div>
              </div>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => handleDelete(c.id)}
                disabled={deletingId === c.id}
                aria-label={`Delete certification ${c.name}`}
              >
                {deletingId === c.id ? 'Deleting...' : 'Delete'}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit} className="space-y-4 rounded-md border p-4" noValidate aria-label="Add certification">
        <h3 className="text-sm font-semibold">Add a certification</h3>
        <div className="space-y-2">
          <Label htmlFor="cert-name">Name</Label>
          <Input
            id="cert-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={submitting}
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? 'cert-name-error' : undefined}
          />
          <FieldError id="cert-name-error" message={errors.name} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cert-issuer">Issuer (optional)</Label>
          <Input id="cert-issuer" value={issuer} onChange={(e) => setIssuer(e.target.value)} disabled={submitting} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cert-issued-on">Issued on (optional)</Label>
          <Input
            id="cert-issued-on"
            type="date"
            value={issuedOn}
            onChange={(e) => setIssuedOn(e.target.value)}
            disabled={submitting}
            aria-invalid={errors.issued_on ? true : undefined}
            aria-describedby={errors.issued_on ? 'cert-issued-on-error' : undefined}
          />
          <FieldError id="cert-issued-on-error" message={errors.issued_on} />
        </div>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Adding...' : 'Add certification'}
        </Button>
      </form>
    </div>
  );
}
