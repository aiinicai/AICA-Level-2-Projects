from django.core.management.base import BaseCommand
from billing.models import Company
class Command(BaseCommand):
    help='Create 10 fictional group companies for LOCAL TESTING ONLY.'
    def handle(self,*args,**kwargs):
        for i in range(1,11):
            code=f'CO{i:02d}'
            # Fictional PIN; keep patterns consistent across generated samples.
            pin=f'A{i:09d}B'
            Company.objects.update_or_create(code=code,defaults={'name':f'Demo Group Company {i:02d} Ltd','kra_pin':pin,'active':True})
        self.stdout.write(self.style.SUCCESS('10 fictional companies available. Demo CO01 PIN: A000000001B'))
