create table if not exists public.zenvia_envios_manuais (
  lote_id uuid not null,
  cliente_id text not null,
  remetente text not null,
  modelo text not null,
  versao text not null,
  dia date not null,
  status text not null check (status in ('processando', 'aceito', 'recusado', 'incerto')),
  mensagem_id text,
  detalhe text,
  criado_em timestamptz not null default now(),
  primary key (lote_id, cliente_id)
);

create unique index if not exists zenvia_envios_manuais_reserva
  on public.zenvia_envios_manuais (cliente_id, modelo, versao, dia)
  where status in ('processando', 'aceito', 'incerto');

alter table public.zenvia_envios_manuais enable row level security;
revoke all on public.zenvia_envios_manuais from public, anon, authenticated;
grant select, insert, update on public.zenvia_envios_manuais to service_role;
