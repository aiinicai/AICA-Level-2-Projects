-- AFTER running setup.sql and creating YOUR account in Authentication > Users:
-- Replace YOUR_EMAIL_HERE with your exact account email. Run this in SQL Editor.
update wl_private.profiles
set role='reviewer', active=true, name='Partner'
where id=(select id from auth.users where lower(email)=lower('subscriptionmail.0112@gmail.com'));

-- Verify that exactly your account was activated:
select p.name,p.role,p.active,u.email
from wl_private.profiles p join auth.users u on u.id=p.id
where p.role='reviewer';
