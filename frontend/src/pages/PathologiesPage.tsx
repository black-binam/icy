import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { apiDelete, apiGet, apiPost, apiPut } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { getErrorMessage } from '@/lib/utils';
import type { Paginated, Pathology, PathologyUpsert } from '@/types/api';

const schema = z.object({
  code: z.string().min(1).max(64),
  label: z.string().min(1).max(255),
  base_care_minutes: z.coerce.number().int().min(1).max(240),
  weight_coefficient: z.coerce.number().min(0.1).max(10),
});

type FormValues = z.infer<typeof schema>;

function emptyValues(): FormValues {
  return { code: '', label: '', base_care_minutes: 15, weight_coefficient: 1 };
}

export default function PathologiesPage() {
  const qc = useQueryClient();
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Pathology | null>(null);

  const { data, isLoading, isError } = useQuery<Paginated<Pathology>>({
    queryKey: ['pathologies'],
    queryFn: () => apiGet<Paginated<Pathology>>('/pathologies?page=1&page_size=100'),
  });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyValues(),
  });

  const openCreate = () => {
    setEditing(null);
    form.reset(emptyValues());
    setOpen(true);
  };

  const openEdit = (p: Pathology) => {
    setEditing(p);
    form.reset({
      code: p.code,
      label: p.label,
      base_care_minutes: p.base_care_minutes,
      weight_coefficient: p.weight_coefficient,
    });
    setOpen(true);
  };

  const upsertMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload: PathologyUpsert = values;
      if (editing) return apiPut<Pathology, PathologyUpsert>(`/pathologies/${editing.id}`, payload);
      return apiPost<Pathology, PathologyUpsert>('/pathologies', payload);
    },
    onSuccess: () => {
      success(editing ? 'Pathologie mise à jour' : 'Pathologie créée');
      qc.invalidateQueries({ queryKey: ['pathologies'] });
      setOpen(false);
    },
    onError: (err) => error('Échec', getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/pathologies/${id}`),
    onSuccess: () => {
      success('Pathologie supprimée');
      qc.invalidateQueries({ queryKey: ['pathologies'] });
    },
    onError: (err) => error('Suppression impossible', getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Pathologies</h1>
          <p className="text-sm text-muted-foreground">
            Référentiel des actes et coefficients de charge.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> Ajouter
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Référentiel</CardTitle>
          <CardDescription>
            {data ? `${data.total} pathologies` : 'Chargement…'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : isError ? (
            <p className="text-sm text-destructive">Chargement impossible.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Libellé</TableHead>
                  <TableHead>Durée base</TableHead>
                  <TableHead>Coef. charge</TableHead>
                  <TableHead className="w-24 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-mono text-xs">{p.code}</TableCell>
                    <TableCell className="font-medium">{p.label}</TableCell>
                    <TableCell>{p.base_care_minutes} min</TableCell>
                    <TableCell>×{p.weight_coefficient.toFixed(2)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEdit(p)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => deleteMutation.mutate(p.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {data && data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                      Aucune pathologie.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Modifier' : 'Nouvelle pathologie'}</DialogTitle>
            <DialogDescription>
              Le coefficient pondère la charge perçue du soin.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={form.handleSubmit((v) => upsertMutation.mutate(v))}
            className="grid grid-cols-2 gap-4"
            noValidate
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="code">Code</Label>
              <Input id="code" {...form.register('code')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="label">Libellé</Label>
              <Input id="label" {...form.register('label')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="base_care_minutes">Durée base (min)</Label>
              <Input
                id="base_care_minutes"
                type="number"
                min={1}
                max={240}
                {...form.register('base_care_minutes')}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="weight_coefficient">Coefficient</Label>
              <Input
                id="weight_coefficient"
                type="number"
                step="0.05"
                min={0.1}
                max={10}
                {...form.register('weight_coefficient')}
              />
            </div>
            <DialogFooter className="col-span-2">
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={upsertMutation.isPending}>
                Enregistrer
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
