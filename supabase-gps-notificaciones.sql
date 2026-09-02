-- Suscripciones a notificaciones push de la app de Carga GPS (sin login).
-- Proyecto Supabase propio: laqwymoxwegemdjlqqya
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

-- La app no tiene login: el jugador (rol anon) da de alta y de baja su propio
-- endpoint de push. Los datos que se guardan (endpoint + claves) no sirven de
-- nada sin la clave VAPID privada, que vive solo en la Edge Function.
-- La policy de SELECT es necesaria para que PostgREST pueda ejecutar el DELETE.
create policy "gps_push ver"        on gps_push_subs for select to anon, authenticated using (true);
create policy "gps_push alta"       on gps_push_subs for insert to anon, authenticated with check (true);
create policy "gps_push actualizar" on gps_push_subs for update to anon, authenticated using (true) with check (true);
create policy "gps_push baja"       on gps_push_subs for delete to anon, authenticated using (true);
