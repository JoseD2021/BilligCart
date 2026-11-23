-- Esquema de Pagos: ejecutar solo si la tabla aun no existe en el entorno.
-- Los pedidos y los estados de entrega existentes no se modifican.
begin;

create table if not exists public."Pagos" (
    payment_id uuid primary key,
    order_id uuid not null references public."Pedidos"(id),
    user_id uuid not null references auth.users(id),
    event_id uuid not null unique,
    provider_session_id text not null unique,
    amount_minor bigint not null check (amount_minor > 0),
    currency text not null check (currency ~ '^[a-z]{3}$'),
    status text not null default 'succeeded' check (status = 'succeeded'),
    livemode boolean not null default false,
    confirmed_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index if not exists pagos_order_idx on public."Pagos" (order_id);
create index if not exists pagos_user_created_idx on public."Pagos" (user_id, created_at desc);
alter table public."Pagos" enable row level security;
revoke all on table public."Pagos" from public, anon, authenticated;
grant select on table public."Pagos" to authenticated;
grant all on table public."Pagos" to service_role;

do $$
begin
    if not exists (
        select 1 from pg_policies where schemaname = 'public'
        and tablename = 'Pagos' and policyname = 'Consultar pagos propios'
    ) then
        create policy "Consultar pagos propios" on public."Pagos"
            for select to authenticated using (user_id = auth.uid());
    end if;
end $$;

commit;
