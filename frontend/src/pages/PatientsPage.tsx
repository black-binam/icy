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
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { apiDelete, apiGet, apiPatch, apiPost } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { getErrorMessage } from '@/lib/utils';
import type { Paginated, Patient, PatientUpsert } from '@/types/api';

const patientSchema = z.object({
  first_name: z.string().min(1, 'Requis').max(120),
  last_name: z.string().min(1, 'Requis').max(120),
  address: z.string().min(3, 'Adresse trop courte').max(500),
  lat: z.coerce.number().min(-90).max(90),
  lon: z.coerce.number().min(-180).max(180),
  phone: z.string().max(40).optional().or(z.literal('')),
  notes: z.string().max(4096).optional().or(z.literal('')),
});

type PatientFormValues = z.infer<typeof patientSchema>;

function emptyValues(): PatientFormValues {
  return { first_name: '', last_name: '', address: '', lat: 0, lon: 0, phone: '', notes: '' };
}

export default function PatientsPage() {
  const qc = useQueryClient();
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Patient | null>(null);

  const { data, isLoading, isError } = useQuery<Paginated<Patient>>({
    queryKey: ['patients'],
    queryFn: () => apiGet<Paginated<Patient>>('/patients?page=1&page_size=100'),
  });

  const form = useForm<PatientFormValues>({
    resolver: zodResolver(patientSchema),
    defaultValues: emptyValues(),
  });

  const openCreate = () => {
    setEditing(null);
    form.reset(emptyValues());
    setOpen(true);
  };

  const openEdit = (p: Patient) => {
    setEditing(p);
    form.reset({
      first_name: p.first_name,
      last_name: p.last_name,
      address: p.address,
      lat: p.lat,
      lon: p.lon,
      phone: p.phone ?? '',
      notes: p.notes ?? '',
    });
    setOpen(true);
  };

  const upsertMutation = useMutation({
    mutationFn: async (values: PatientFormValues) => {
      const payload: PatientUpsert = {
        first_name: values.first_name,
        last_name: values.last_name,
        address: values.address,
        lat: values.lat,
        lon: values.lon,
        phone: values.phone ? values.phone : null,
        notes: values.notes ? values.notes : null,
      };
      if (editing) {
        return apiPatch<Patient, PatientUpsert>(`/patients/${editing.id}`, payload);
      }
      return apiPost<Patient, PatientUpsert>('/patients', payload);
    },
    onSuccess: () => {
      success(editing ? 'Patient mis à jour' : 'Patient créé');
      qc.invalidateQueries({ queryKey: ['patients'] });
      setOpen(false);
    },
    onError: (err) => error('Échec', getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/patients/${id}`),
    onSuccess: () => {
      success('Patient supprimé');
      qc.invalidateQueries({ queryKey: ['patients'] });
    },
    onError: (err) => error('Suppression impossible', getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Patients</h1>
          <p className="text-sm text-muted-foreground">
            Fiches patients et coordonnées de visite.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> Ajouter
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Liste</CardTitle>
          <CardDescription>
            {data ? `${data.total} patient${data.total > 1 ? 's' : ''}` : 'Chargement…'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : isError ? (
            <p className="text-sm text-destructive">Chargement impossible.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Adresse</TableHead>
                  <TableHead>Pathologies</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="w-24 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">
                      {p.last_name.toUpperCase()} {p.first_name}
                    </TableCell>
                    <TableCell className="max-w-[28ch] truncate text-muted-foreground">
                      {p.address}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {p.pathologies.map((pp) => (
                          <Badge key={pp.pathology_id} variant="secondary">
                            {pp.pathology?.code ?? `#${pp.pathology_id}`}
                          </Badge>
                        ))}
                        {p.pathologies.length === 0 && (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {p.is_active ? (
                        <Badge variant="success">Actif</Badge>
                      ) : (
                        <Badge variant="secondary">Inactif</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEdit(p)}
                          aria-label="Modifier"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteMutation.mutate(p.id)}
                          aria-label="Supprimer"
                          className="text-destructive hover:text-destructive"
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
                      Aucun patient. Cliquez sur « Ajouter » pour commencer.
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
            <DialogTitle>{editing ? 'Modifier le patient' : 'Nouveau patient'}</DialogTitle>
            <DialogDescription>
              Saisissez les informations de prise en charge.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={form.handleSubmit((v) => upsertMutation.mutate(v))}
            className="grid grid-cols-2 gap-4"
            noValidate
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="last_name">Nom</Label>
              <Input id="last_name" {...form.register('last_name')} />
              {form.formState.errors.last_name && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.last_name.message}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="first_name">Prénom</Label>
              <Input id="first_name" {...form.register('first_name')} />
              {form.formState.errors.first_name && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.first_name.message}
                </p>
              )}
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="address">Adresse</Label>
              <Input id="address" {...form.register('address')} />
              {form.formState.errors.address && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.address.message}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="lat">Latitude</Label>
              <Input id="lat" type="number" step="any" {...form.register('lat')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="lon">Longitude</Label>
              <Input id="lon" type="number" step="any" {...form.register('lon')} />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="phone">Téléphone</Label>
              <Input id="phone" {...form.register('phone')} />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="notes">Notes</Label>
              <Input id="notes" {...form.register('notes')} />
            </div>
            <DialogFooter className="col-span-2">
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={upsertMutation.isPending}>
                {upsertMutation.isPending ? 'Enregistrement…' : 'Enregistrer'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
