import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { registerPwa } from './pwa/register';

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('Root container #root introuvable dans index.html');
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Active le service worker (no-op en dev).
registerPwa();
