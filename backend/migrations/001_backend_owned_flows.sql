-- Ejecutar en el editor SQL de Supabase antes de desplegar el backend.
-- Los nombres respetan las tablas que ya utiliza el proyecto.
begin;

alter table public."Preferencias"
    add column if not exists restricciones jsonb not null default '[]'::jsonb,
    add column if not exists presupuesto_semanal numeric not null default 0;

create table if not exists public."Pedidos" (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id),
    menu_id bigint not null references public."Menu"(id),
    checkout_key text not null,
    items jsonb not null,
    total numeric not null check (total >= 0),
    estado text not null default 'pendiente' constraint pedidos_estado_check
        check (estado in ('pendiente', 'confirmado', 'en_camino', 'entregado')),
    repartidor_id uuid references auth.users(id),
    repartidor text,
    tiempo_estimado text,
    created_at timestamptz not null default now()
);

-- Compatibilidad con una tabla Pedidos usada previamente por el servicio GPS.
alter table public."Pedidos"
    add column if not exists menu_id bigint references public."Menu"(id),
    add column if not exists checkout_key text,
    add column if not exists items jsonb not null default '[]'::jsonb,
    add column if not exists total numeric not null default 0,
    add column if not exists estado text not null default 'pendiente' constraint pedidos_estado_check
        check (estado in ('pendiente', 'confirmado', 'en_camino', 'entregado')),
    add column if not exists repartidor text,
    add column if not exists tiempo_estimado text,
    add column if not exists created_at timestamptz not null default now();

create unique index if not exists pedidos_checkout_unique on public."Pedidos" (user_id, checkout_key);
create index if not exists pedidos_user_created on public."Pedidos" (user_id, created_at desc);

-- Auth sigue siendo público. Las tablas se usan exclusivamente desde el servidor,
-- con SUPABASE_KEY=service_role o sb_secret_..., nunca una clave pública.
alter table public."Menu" enable row level security;
alter table public."Plato" enable row level security;
alter table public."Ingrediente" enable row level security;
alter table public."PlatoIngrediente" enable row level security;
alter table public."Preferencias" enable row level security;
alter table public."Pedidos" enable row level security;

revoke all on table public."Menu", public."Plato", public."Ingrediente",
    public."PlatoIngrediente", public."Preferencias", public."Pedidos" from anon, authenticated;
grant all on table public."Menu", public."Plato", public."Ingrediente",
    public."PlatoIngrediente", public."Preferencias", public."Pedidos" to service_role;

commit;
