-- Dirección de entrega del pedido (destino del cliente):
--   direccion_dest  texto con la dirección
--   referencias     indicaciones opcionales (portería, torre, punto de referencia)
--   lat_dest/lng_dest  coordenadas; las completa el mapa/GPS, mientras tanto quedan en null
-- Si las columnas ya existen no se tocan (add column if not exists).
-- Ejecutar en el editor SQL de Supabase.
begin;

alter table public."Pedidos"
    add column if not exists direccion_dest text,
    add column if not exists referencias text,
    add column if not exists lat_dest double precision,
    add column if not exists lng_dest double precision;

notify pgrst, 'reload schema';

commit;
