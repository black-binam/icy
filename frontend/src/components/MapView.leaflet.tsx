import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { MapViewProps } from './MapView';

/**
 * Implémentation Leaflet concrète, chargée en lazy depuis MapView.
 *
 * Corrige le souci connu des marqueurs par défaut quand le bundler ne
 * détecte pas les PNG dans node_modules. On définit une icône SVG inline
 * teintée côté primaire.
 */

const baseIcon = L.divIcon({
  className: 'icy-marker',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  html: `<span style="
    display:block;width:22px;height:22px;border-radius:9999px;
    background:#1f7876;border:3px solid #fff;
    box-shadow:0 2px 6px rgba(15,23,42,0.25);
  "></span>`,
});

function coloredIcon(color: string) {
  return L.divIcon({
    className: 'icy-marker',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    html: `<span style="
      display:block;width:22px;height:22px;border-radius:9999px;
      background:${color};border:3px solid #fff;
      box-shadow:0 2px 6px rgba(15,23,42,0.25);
    "></span>`,
  });
}

function Recenter({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom(), { animate: true });
  }, [center, map]);
  return null;
}

export default function LeafletMap({
  points,
  polylines = [],
  center,
  zoom = 12,
}: MapViewProps) {
  const tilesUrl =
    import.meta.env.VITE_MAP_TILES_URL ?? 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

  const resolvedCenter: [number, number] =
    center ??
    (points.length > 0
      ? [points[0]!.lat, points[0]!.lon]
      : [46.603354, 1.888334]);

  return (
    <MapContainer
      center={resolvedCenter}
      zoom={zoom}
      scrollWheelZoom
      className="h-full w-full"
      style={{ height: '100%', width: '100%' }}
    >
      <Recenter center={resolvedCenter} />
      <TileLayer
        url={tilesUrl}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      {points.map((p, idx) => (
        <Marker
          key={`${p.lat}-${p.lon}-${idx}`}
          position={[p.lat, p.lon]}
          icon={p.color ? coloredIcon(p.color) : baseIcon}
        >
          <Popup>{p.label}</Popup>
        </Marker>
      ))}
      {polylines.map((line, idx) => (
        <Polyline
          key={`line-${idx}`}
          positions={line.points}
          pathOptions={{ color: line.color, weight: 4, opacity: 0.85 }}
        />
      ))}
    </MapContainer>
  );
}
