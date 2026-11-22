-- Unifica el ciclo de vida del pedido en una sola columna de texto.
-- Ejecutar en el editor SQL de Supabase en bases que ya tengan public."Pedidos".
begin;

alter table public."Pedidos"
    add column if not exists estado text;

do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'Pedidos'
          and column_name = 'etapa'
    ) then
        execute $sql$
            update public."Pedidos"
            set estado = case
                when estado in ('pendiente', 'confirmado', 'en_camino', 'entregado') then estado
                when estado = 'preparando' then 'confirmado'
                when estado = '1' then 'confirmado'
                when estado = '2' then 'en_camino'
                when estado = '3' then 'entregado'
                when etapa = 3 then 'entregado'
                when etapa = 2 then 'en_camino'
                when etapa = 1 then 'confirmado'
                else 'pendiente'
            end
            where estado is null
               or estado not in ('pendiente', 'confirmado', 'en_camino', 'entregado')
        $sql$;
    else
        update public."Pedidos"
        set estado = case
            when estado = 'preparando' then 'confirmado'
            when estado = '1' then 'confirmado'
            when estado = '2' then 'en_camino'
            when estado = '3' then 'entregado'
            else 'pendiente'
        end
        where estado is null
           or estado not in ('pendiente', 'confirmado', 'en_camino', 'entregado');
    end if;
end $$;

alter table public."Pedidos"
    alter column estado set default 'pendiente',
    alter column estado set not null;

alter table public."Pedidos" drop constraint if exists pedidos_estado_check;
alter table public."Pedidos"
    add constraint pedidos_estado_check
    check (estado in ('pendiente', 'confirmado', 'en_camino', 'entregado'));

alter table public."Pedidos" drop column if exists etapa;

create index if not exists pedidos_estado_idx on public."Pedidos" (estado);

commit;
