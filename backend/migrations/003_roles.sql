-- Roles de usuarios: el registro lo escribe desde el backend con service key.
begin;

create table if not exists public."Roles" (
    user_id uuid primary key references auth.users(id) on delete cascade,
    rol varchar(20) not null default 'user'
);

alter table public."Roles" drop constraint if exists roles_rol_check;
alter table public."Roles"
    add constraint roles_rol_check check (rol in ('user', 'admin', 'repartidor'));

alter table public."Roles" enable row level security;

revoke all on table public."Roles" from anon, authenticated;
grant select, insert, update, delete on table public."Roles" to service_role;

commit;
