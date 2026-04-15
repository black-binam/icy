import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { CSS } from '@dnd-kit/utilities';
import { format } from 'date-fns';
import { GripVertical, MapPin, Sparkles } from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { MapView, routeToMapProps, useMapCenter } from '@/components/MapView';
import { apiGet, apiPost, apiPut } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { getErrorMessage, formatMinutes, minutesToClock } from '@/lib/utils';
import type { OptimizeParams, OptimizeResult, Paginated, Route, RouteStop } from '@/types/api';

const DEFAULT_PARAMS: OptimizeParams = {
  date: format(new Date(), 'yyyy-MM-dd'),
  alpha_distance: 1,
  beta_balance: 1,
  gamma_time: 1,
  time_limit_seconds: 20,
};

/* ---------- Drag handle row ---------- */

function SortableStop({ stop }: { stop: RouteStop }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: stop.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  };
  return (
    <li
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 rounded-xl border border-border bg-card px-3 py-2 shadow-soft"
    >
      <button
        {...attributes}
        {...listeners}
        aria-label="Réordonner"
        className="cursor-grab text-muted-foreground hover:text-foreground active:cursor-grabbing"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <Badge variant="outline" className="font-mono">
        #{stop.sequence}
      </Badge>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          {stop.patient
            ? `${stop.patient.last_name.toUpperCase()} ${stop.patient.first_name}`
            : `Patient #${stop.patient_id}`}
        </p>
        {stop.patient?.address && (
          <p className="truncate text-xs text-muted-foreground">{stop.patient.address}</p>
        )}
      </div>
      <span className="shrink-0 font-mono text-xs text-muted-foreground">
        {minutesToClock(stop.arrival_minutes)} → {minutesToClock(stop.departure_minutes)}
      </span>
    </li>
  );
}

/* ---------- Single route card with DnD ---------- */

function RouteCard({
  route,
  onReorder,
}: {
  route: Route;
  onReorder: (routeId: number, stopIds: number[]) => void;
}) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  const [stops, setStops] = useState<RouteStop[]>(() =>
    [...route.stops].sort((a, b) => a.sequence - b.sequence),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = stops.findIndex((s) => s.id === active.id);
    const newIndex = stops.findIndex((s) => s.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const next = arrayMove(stops, oldIndex, newIndex);
    setStops(next);
    onReorder(route.id, next.map((s) => s.id));
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base">
              {route.caregiver
                ? `${route.caregiver.last_name.toUpperCase()} ${route.caregiver.first_name}`
                : `Soignant #${route.caregiver_id}`}
            </CardTitle>
            <CardDescription>
              {stops.length} arrêts · {formatMinutes(route.total_duration_minutes)} ·{' '}
              {(route.total_distance_m / 1000).toFixed(1)} km
            </CardDescription>
          </div>
          <Badge variant={route.status === 'done' ? 'success' : 'default'}>{route.status}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          modifiers={[restrictToVerticalAxis]}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={stops.map((s) => s.id)} strategy={verticalListSortingStrategy}>
            <ul className="flex flex-col gap-2">
              {stops.map((stop) => (
                <SortableStop key={stop.id} stop={stop} />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
        {stops.length === 0 && (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Aucun arrêt sur cette tournée.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------- Page ---------- */

export default function RoutesPage() {
  const qc = useQueryClient();
  const { success, error } = useToast();
  const [panelOpen, setPanelOpen] = useState(false);
  const [params, setParams] = useState<OptimizeParams>(DEFAULT_PARAMS);

  const { data, isLoading, isError } = useQuery<Paginated<Route>>({
    queryKey: ['routes', params.date],
    queryFn: () =>
      apiGet<Paginated<Route>>(`/routes?date=${encodeURIComponent(params.date)}&page_size=100`),
  });

  const optimize = useMutation({
    mutationFn: (p: OptimizeParams) => apiPost<OptimizeResult, OptimizeParams>('/routes/optimize', p),
    onSuccess: (res) => {
      success(
        'Optimisation terminée',
        `${res.routes.length} tournées · σ = ${res.workload_stddev.toFixed(1)} min`,
      );
      qc.invalidateQueries({ queryKey: ['routes'] });
      setPanelOpen(false);
    },
    onError: (err) => error('Échec de l’optimisation', getErrorMessage(err)),
  });

  const reorder = useMutation({
    mutationFn: async ({ routeId, stopIds }: { routeId: number; stopIds: number[] }) =>
      apiPut<Route>(`/routes/${routeId}/stops/order`, { stop_ids: stopIds }),
    onError: (err) => error('Réordonnancement impossible', getErrorMessage(err)),
  });

  const routes = data?.items ?? [];
  const { points, polylines } = useMemo(() => routeToMapProps(routes), [routes]);
  const center = useMapCenter(points);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tournées</h1>
          <p className="text-sm text-muted-foreground">
            Visualisation, édition et optimisation automatique des tournées du jour.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="date"
            value={params.date}
            onChange={(e) => setParams((p) => ({ ...p, date: e.target.value }))}
            className="w-44"
            aria-label="Date"
          />
          <Button onClick={() => setPanelOpen(true)}>
            <Sparkles className="h-4 w-4" /> Optimiser
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <MapPin className="h-4 w-4" /> Carte des tournées
          </CardTitle>
          <CardDescription>
            Polylignes colorées par soignant ; marqueurs numérotés dans l’ordre.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MapView points={points} polylines={polylines} center={center} height={440} />
        </CardContent>
      </Card>

      <Separator />

      <section className="grid gap-4 lg:grid-cols-2">
        {isLoading && (
          <>
            <Skeleton className="h-60 w-full rounded-2xl" />
            <Skeleton className="h-60 w-full rounded-2xl" />
          </>
        )}
        {isError && (
          <p className="text-sm text-destructive">Chargement des tournées impossible.</p>
        )}
        {routes.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            onReorder={(routeId, stopIds) => reorder.mutate({ routeId, stopIds })}
          />
        ))}
        {!isLoading && routes.length === 0 && (
          <Card className="lg:col-span-2">
            <CardContent className="py-12 text-center">
              <p className="text-sm text-muted-foreground">
                Aucune tournée pour cette date. Lancez une optimisation pour en générer.
              </p>
            </CardContent>
          </Card>
        )}
      </section>

      <Dialog open={panelOpen} onOpenChange={setPanelOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Paramètres d’optimisation</DialogTitle>
            <DialogDescription>
              Pondérations multi-critères (distance / équité / fenêtres) et budget solveur.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="opt-date">Date</Label>
              <Input
                id="opt-date"
                type="date"
                value={params.date}
                onChange={(e) => setParams((p) => ({ ...p, date: e.target.value }))}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="alpha">α distance</Label>
              <Input
                id="alpha"
                type="number"
                step="0.1"
                min={0}
                max={10}
                value={params.alpha_distance}
                onChange={(e) =>
                  setParams((p) => ({ ...p, alpha_distance: Number(e.target.value) }))
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="beta">β équité</Label>
              <Input
                id="beta"
                type="number"
                step="0.1"
                min={0}
                max={10}
                value={params.beta_balance}
                onChange={(e) =>
                  setParams((p) => ({ ...p, beta_balance: Number(e.target.value) }))
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="gamma">γ fenêtres</Label>
              <Input
                id="gamma"
                type="number"
                step="0.1"
                min={0}
                max={10}
                value={params.gamma_time}
                onChange={(e) => setParams((p) => ({ ...p, gamma_time: Number(e.target.value) }))}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="budget">Budget solveur (s)</Label>
              <Input
                id="budget"
                type="number"
                min={5}
                max={120}
                value={params.time_limit_seconds}
                onChange={(e) =>
                  setParams((p) => ({ ...p, time_limit_seconds: Number(e.target.value) }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPanelOpen(false)}>
              Annuler
            </Button>
            <Button disabled={optimize.isPending} onClick={() => optimize.mutate(params)}>
              {optimize.isPending ? 'Optimisation…' : 'Lancer'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
