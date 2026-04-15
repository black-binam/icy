/**
 * Enregistrement du service worker via vite-plugin-pwa.
 *
 * - En production : autoUpdate (cf. vite.config.ts).
 * - En dev : aucun SW (évite les caches gênants).
 */
import { registerSW } from 'virtual:pwa-register';

export function registerPwa(): void {
  if (import.meta.env.DEV) return;
  try {
    registerSW({
      immediate: true,
      onRegisteredSW(_swUrl, _registration) {
        // Ne pas logger l'URL en production ; rien d'utile à tracer ici.
      },
      onRegisterError() {
        // Silencieux : la PWA est progressive enhancement.
      },
    });
  } catch {
    /* virtual module indisponible — ignoré */
  }
}
