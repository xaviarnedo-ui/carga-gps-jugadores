-- Suscripciones a notificaciones push de la app de Carga GPS (sin login).
-- Reutiliza el mismo proyecto Supabase que la app de hábitos.
-- Ejecútalo una vez en el SQL Editor de Supabase.

create table if not exists gps_push_subs (
  id         uuid primary key default gen_random_uuid(),
  dorsal     int,
  endpoint   text not null unique,
  p256dh     text not null,
  auth       text not null,
  user_agent text,
  created_at timestamptz not null default now()
);

alter table gps_push_subs enable row level security;

-- La app no tiene login. El jugador (rol anon) puede darse de alta y de baja,
-- pero NADIE con la anon key puede LEER la lista (no hay policy de select):
-- solo la Edge Function, que usa la service_role key, puede leerla para enviar.
create policy "gps_push alta"        on gps_push_subs for insert to anon, authenticated with check (true);
create policy "gps_push actualizar"  on gps_push_subs for update to anon, authenticated using (true) with check (true);
create policy "gps_push baja"        on gps_push_subs for delete to anon, authenticated using (true);
