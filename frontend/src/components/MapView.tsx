import { lazy, Suspense, useMemo } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import type { Route } from '@/types/api';

/**
 * Chargement dynamique de react-leaflet pour éviter l'exécution du code
 * Leaflet côté SSR / au premier bytecode (il manipule `window`).
 */
const LeafletMap = lazy(() => import('./MapView.leaflet'));

export interface MapPoint {
  lat: number;
  lon: number;
  label: string;
  /** Couleur hex pour regrouper visuellement les stops d'une même tournée. */
  color?: string;
}

export interface MapPolyline {
  color: string;
  points: Array<[number, number]>;
}

export interface MapViewProps {
  points: MapPoint[];
  polylines?: MapPolyline[];
  /** Centre initial ; sinon calculé depuis les points. */
  center?: [number, number];
  zoom?: number;
  height?: number | string;
}

export function MapView(props: MapViewProps) {
  const fallback = (
    <Skeleton
      className="h-full min-h-[320px] w-full rounded-2xl"
      style={{ height: props.height ?? 420 }}
    />
  );
  return (
    <div
      className="w-full overflow-hidden rounded-2xl border border-border shadow-soft"
      style={{ height: props.height ?? 420 }}
    >
      <Suspense fallback={fallback}>
        <LeafletMap {...props} />
      </Suspense>
    </div>
  );
}

/* ----------- Helpers de mapping Route → props ----------- */

const PALETTE = ['#1f7876', '#0f766e', '#0ea5e9', '#6366f1', '#d97706', '#db2777', '#16a34a'];

export function routeToMapProps(routes: Route[]): {
  points: MapPoint[];
  polylines: MapPolyline[];
} {
  const points: MapPoint[] = [];
  const polylines: MapPolyline[] = [];
  routes.forEach((route, idx) => {
    const color = PALETTE[idx % PALETTE.length]!;
    const pts: Array<[number, number]> = [];
    if (route.caregiver) {
      pts.push([route.caregiver.home_base_lat, route.caregiver.home_base_lon]);
    }
    route.stops
      .slice()
      .sort((a, b) => a.sequence - b.sequence)
      .forEach((stop) => {
        if (!stop.patient) return;
        points.push({
          lat: stop.patient.lat,
          lon: stop.patient.lon,
          label: `${stop.sequence}. ${stop.patient.first_name} ${stop.patient.last_name}`,
          color,
        });
        pts.push([stop.patient.lat, stop.patient.lon]);
      });
    if (pts.length >= 2) polylines.push({ color, points: pts });
  });
  return { points, polylines };
}

export function useMapCenter(points: MapPoint[]): [number, number] {
  return useMemo(() => {
    if (points.length === 0) return [46.603354, 1.888334]; // centre France
    const lat = points.reduce((s, p) => s + p.lat, 0) / points.length;
    const lon = points.reduce((s, p) => s + p.lon, 0) / points.length;
    return [lat, lon];
  }, [points]);
}
