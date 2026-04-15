import { useQuery } from '@tanstack/react-query';
import { Activity, Users, Stethoscope, Route as RouteIcon } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { WorkloadBadge } from '@/components/WorkloadBadge';
import { apiGet } from '@/lib/api';
import type { DashboardKpis } from '@/types/api';

interface KpiItem {
  label: string;
  value: number | string;
  icon: typeof Activity;
  hint?: string;
}

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery<DashboardKpis>({
    queryKey: ['dashboard', 'kpis'],
    queryFn: () => apiGet<DashboardKpis>('/dashboard/kpis'),
    staleTime: 60_000,
  });

  const items: KpiItem[] = [
    {
      label: 'Soignants actifs',
      value: data?.active_caregivers ?? '—',
      icon: Stethoscope,
    },
    {
      label: 'Patients suivis',
      value: data?.active_patients ?? '—',
      icon: Users,
    },
    {
      label: 'Tournées du jour',
      value: data?.today_routes ?? '—',
      hint: data ? `${data.today_stops} arrêts programmés` : undefined,
      icon: RouteIcon,
    },
    {
      label: 'Écart-type charge',
      value: data ? `${data.workload_stddev_minutes.toFixed(1)} min` : '—',
      hint: 'Plus c’est bas, plus l’équité est bonne.',
      icon: Activity,
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Tableau de bord</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Synthèse de l’activité du jour et équité de la charge de travail.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {item.label}
                </CardTitle>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-4 w-4" aria-hidden />
                </div>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <Skeleton className="h-8 w-24" />
                ) : (
                  <span className="text-3xl font-semibold tracking-tight">{item.value}</span>
                )}
                {item.hint && (
                  <p className="mt-1 text-xs text-muted-foreground">{item.hint}</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Équité de la charge par soignant</CardTitle>
          <CardDescription>
            Répartition comparée de la charge planifiée vs. capacité journalière.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          {isLoading && (
            <>
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </>
          )}
          {isError && (
            <p className="text-sm text-destructive">Impossible de charger les indicateurs.</p>
          )}
          {data && data.per_caregiver_workload.length === 0 && (
            <p className="text-sm text-muted-foreground">Aucun soignant actif pour le moment.</p>
          )}
          {data?.per_caregiver_workload.map((row) => (
            <WorkloadBadge
              key={row.caregiver_id}
              label={row.caregiver_name}
              minutes={row.workload_minutes}
              capacityMinutes={row.capacity_minutes}
            />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
