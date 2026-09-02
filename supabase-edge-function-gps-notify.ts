// Edge Function "gps-notify" — envía una notificación push a todos los
// jugadores suscritos de la app de Carga GPS.
// La llama import_data.py --avisar despues de regenerar data.js.
// Instrucciones de despliegue al final del archivo.

import { createClient } from 'npm:@supabase/supabase-js@2';
import webpush from 'npm:web-push@3.6.7';

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const VAPID_PUBLIC_KEY = Deno.env.get('VAPID_PUBLIC_KEY')!;
const VAPID_PRIVATE_KEY = Deno.env.get('VAPID_PRIVATE_KEY')!;
const GPS_NOTIFY_SECRET = Deno.env.get('GPS_NOTIFY_SECRET')!;

webpush.setVapidDetails('mailto:xavi.arnedo@gmail.com', VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY);

Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }
  // Auth propia: la anon key es pública, así que exigimos un secreto compartido.
  if (req.headers.get('x-gps-secret') !== GPS_NOTIFY_SECRET) {
    return new Response(JSON.stringify({ error: 'unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch (_) { /* body opcional */ }
  const title = (body.title as string) || 'Carga GPS';
  const msg = (body.body as string) || 'Datos de GPS actualizados';
  const url = (body.url as string) || './jugador.html';

  const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const { data: subs, error } = await supabase.from('gps_push_subs').select('*');
  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  const payload = JSON.stringify({ title, body: msg, url });
  let sent = 0, removed = 0;

  for (const sub of subs || []) {
    try {
      await webpush.sendNotification(
        { endpoint: sub.endpoint, keys: { p256dh: sub.p256dh, auth: sub.auth } },
        payload,
      );
      sent++;
    } catch (err) {
      const code = (err as { statusCode?: number }).statusCode;
      if (code === 404 || code === 410) {
        await supabase.from('gps_push_subs').delete().eq('id', sub.id);
        removed++;
      }
    }
  }

  return new Response(JSON.stringify({ sent, removed, total: (subs || []).length }), {
    headers: { 'Content-Type': 'application/json' },
  });
});

/*
CÓMO DESPLEGAR (todo desde el dashboard de Supabase, sin instalar nada):

1. Ejecuta supabase-gps-notificaciones.sql en el SQL Editor (crea la tabla).

2. Edge Functions -> Deploy a new function (editor del navegador) -> nombre: gps-notify
   Pega este código (sin este comentario final).
   IMPORTANTE: desactiva "Verify JWT" para esta función (la protege x-gps-secret).

3. Edge Functions -> Secrets (Manage secrets). Añade los 3:
     GPS_NOTIFY_SECRET  = (el mismo valor que tienes en tu .env local)
     VAPID_PUBLIC_KEY   = (la del .env / jugador.js)
     VAPID_PRIVATE_KEY  = (la del .env)
   SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY los inyecta Supabase solo.

4. NO hace falta cron: la función se dispara solo cuando tú ejecutas
   `python3 import_data.py --avisar`.
*/
