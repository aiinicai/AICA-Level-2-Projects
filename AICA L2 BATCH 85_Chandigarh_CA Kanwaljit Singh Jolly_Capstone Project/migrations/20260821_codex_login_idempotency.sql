-- Keep one reusable interactive Codex login per tenant. This prevents double
-- clicks or multiple browser tabs from cancelling a login already in progress.
begin;

update tenant_codex_login_sessions
set status = 'EXPIRED', updated_at = now()
where status in ('QUEUED', 'WAITING_FOR_USER') and expires_at <= now();

with duplicates as (
    select id, row_number() over (
        partition by tenant_id order by created_at desc, id desc
    ) as position
    from tenant_codex_login_sessions
    where status in ('QUEUED', 'WAITING_FOR_USER')
)
update tenant_codex_login_sessions
set status = 'CANCELLED', updated_at = now()
where id in (select id from duplicates where position > 1);

create unique index if not exists tenant_codex_login_one_active_per_tenant
    on tenant_codex_login_sessions(tenant_id)
    where status in ('QUEUED', 'WAITING_FOR_USER');

commit;
