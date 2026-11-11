-- 1) Create your first admin in Supabase Dashboard > Authentication > Users.
-- 2) Copy the user's UUID and replace the placeholder below.
-- 3) Run this once in SQL Editor. Never run it from the frontend.
with org as (
 insert into public.organizations(name) values ('SmartHire Capstone') returning id
)
insert into public.profiles(user_id,organization_id,role,full_name)
select 'REPLACE_WITH_ADMIN_AUTH_USER_UUID'::uuid,id,'admin','Capstone Admin' from org;
