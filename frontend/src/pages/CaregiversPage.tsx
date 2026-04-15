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
import { Badge } from '@/components/ui/badge';
import { apiDelete, apiGet, apiPost, apiPut } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { getErrorMessage, formatMinutes } from '@/lib/utils';
import type { Caregiver, CaregiverUpsert, Paginated } from '@/types/api';

const schema = z.object({
  first_name: z.string().min(1).max(120),
  last_name: z.string().min(1).max(120),
  home_base_lat: z.coerce.number().min(-90).max(90),
  home_base_lon: z.coerce.number().min(-180).max(180),
  daily_capacity_minutes: z.coerce.number().int().min(60).max(12 * 60),
  skills: z.string().optional().default(''),
});

type FormValues = z.infer<typeof schema>;

function emptyValues(): FormValues {
  return {
    first_name: '',
    last_name: '',
    home_base_lat: 0,
    home_base_lon: 0,
    daily_capacity_minutes: 420,
    skills: '',
  };
}

export default function CaregiversPage() {
  const qc = useQueryClient();
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Caregiver | null>(null);

  const { data, isLoading, isError } = useQuery<Paginated<Caregiver>>({
    queryKey: ['caregivers'],
    queryFn: () => apiGet<Paginated<Caregiver>>('/caregivers?page=1&page_size=100'),
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

  const openEdit = (c: Caregiver) => {
    setEditing(c);
    form.reset({
      first_name: c.first_name,
      last_name: c.last_name,
      home_base_lat: c.home_base_lat,
      home_base_lon: c.home_base_lon,
      daily_capacity_minutes: c.daily_capacity_minutes,
      skills: c.skills.join(', '),
    });
    setOpen(true);
  };

  const upsertMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload: CaregiverUpsert = {
        first_name: values.first_name,
        last_name: values.last_name,
        home_base_lat: values.home_base_lat,
        home_base_lon: values.home_base_lon,
        daily_capacity_minutes: values.daily_capacity_minutes,
        skills: values.skills
          ? values.skills.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
      };
      if (editing) return apiPut<Caregiver, CaregiverUpsert>(`/caregivers/${editing.id}`, payload);
      return apiPost<Caregiver, CaregiverUpsert>('/caregivers', payload);
    },
    onSuccess: () => {
      success(editing ? 'Soignant mis à jour' : 'Soignant créé');
      qc.invalidateQueries({ queryKey: ['caregivers'] });
      setOpen(false);
    },
    onError: (err) => error('Échec', getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiDelete(`/caregivers/${id}`),
    onSuccess: () => {
      success('Soignant supprimé');
      qc.invalidateQueries({ queryKey: ['caregivers'] });
    },
    onError: (err) => error('Suppression impossible', getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Soignants</h1>
          <p className="text-sm text-muted-foreground">
            Base de départ, capacité journalière et compétences.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" /> Ajouter
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Équipe</CardTitle>
          <CardDescription>
            {data ? `${data.total} soignant${data.total > 1 ? 's' : ''}` : 'Chargement…'}
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
                  <TableHead>Nom</TableHead>
                  <TableHead>Base</TableHead>
                  <TableHead>Capacité</TableHead>
                  <TableHead>Compétences</TableHead>
                  <TableHead className="w-24 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">
                      {c.last_name.toUpperCase()} {c.first_name}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {c.home_base_lat.toFixed(4)}, {c.home_base_lon.toFixed(4)}
                    </TableCell>
                    <TableCell>{formatMinutes(c.daily_capacity_minutes)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {c.skills.map((s) => (
                          <Badge key={s} variant="secondary">
                            {s}
                          </Badge>
                        ))}
                        {c.skills.length === 0 && (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEdit(c)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => deleteMutation.mutate(c.id)}
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
                      Aucun soignant.
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
            <DialogTitle>{editing ? 'Modifier' : 'Nouveau soignant'}</DialogTitle>
            <DialogDescription>Informations professionnelles.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={form.handleSubmit((v) => upsertMutation.mutate(v))}
            className="grid grid-cols-2 gap-4"
            noValidate
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="last_name">Nom</Label>
              <Input id="last_name" {...form.register('last_name')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="first_name">Prénom</Label>
              <Input id="first_name" {...form.register('first_name')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="home_base_lat">Latitude base</Label>
              <Input id="home_base_lat" type="number" step="any" {...form.register('home_base_lat')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="home_base_lon">Longitude base</Label>
              <Input id="home_base_lon" type="number" step="any" {...form.register('home_base_lon')} />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="daily_capacity_minutes">Capacité journalière (min)</Label>
              <Input
                id="daily_capacity_minutes"
                type="number"
                min={60}
                max={720}
                {...form.register('daily_capacity_minutes')}
              />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="skills">Compétences (séparées par virgules)</Label>
              <Input id="skills" placeholder="pansement, injection, toilette" {...form.register('skills')} />
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
