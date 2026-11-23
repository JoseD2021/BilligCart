-- Dirección de entrega del pedido: {direccion, referencia, lat, lng}.
-- lat/lng los completa el mapa/GPS del cliente; mientras tanto solo se guarda el texto.
-- Ejecutar en el editor SQL de Supabase.
begin;

alter table public."Pedidos"
    add column if not exists envio jsonb;

notify pgrst, 'reload schema';

commit;
