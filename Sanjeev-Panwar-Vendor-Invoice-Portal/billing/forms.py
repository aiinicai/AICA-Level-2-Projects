from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Company,VendorProfile,Invoice,kra_pin_validator

class SignupForm(forms.Form):
    legal_name=forms.CharField(max_length=200)
    kra_pin=forms.CharField(max_length=11,label='Vendor KRA PIN')
    email=forms.EmailField()
    password1=forms.CharField(widget=forms.PasswordInput,label='Password')
    password2=forms.CharField(widget=forms.PasswordInput,label='Confirm password')
    def clean_kra_pin(self):
        x=self.cleaned_data['kra_pin'].strip().upper();kra_pin_validator(x);return x
    def clean_email(self):
        x=self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username__iexact=x).exists() or User.objects.filter(email__iexact=x).exists():raise ValidationError('Email is already registered.')
        return x
    def clean(self):
        data=super().clean()
        if data.get('password1')!=data.get('password2'):self.add_error('password2','Passwords do not match.')
        if data.get('password1'):
            try: validate_password(data['password1'])
            except ValidationError as e:self.add_error('password1',e)
        return data

class UploadForm(forms.Form):
    company=forms.ModelChoiceField(queryset=Company.objects.filter(active=True))
    invoice=forms.FileField(help_text='PDF, JPG or PNG. Required.')
    purchase_order=forms.FileField(help_text='PDF, JPG or PNG. Required.')
    supporting_documents=forms.FileField(required=False,widget=forms.ClearableFileInput(attrs={'accept':'.pdf,.jpg,.jpeg,.png'}),help_text='Optional single supporting document in this pilot.')
    vendor_notes=forms.CharField(required=False,widget=forms.Textarea(attrs={'rows':2}),max_length=1000)

class ReviewForm(forms.ModelForm):
    class Meta:
        model=Invoice
        fields=['invoice_number','invoice_date','currency','net_amount','vat_amount','total_amount','po_number','finance_notes']
        widgets={'invoice_date':forms.DateInput(attrs={'type':'date'}),'finance_notes':forms.Textarea(attrs={'rows':3})}
    def clean_currency(self):
        c=self.cleaned_data['currency'].upper().strip()
        if len(c)!=3 or not c.isalpha():raise ValidationError('Enter a three-letter currency code such as KES or USD.')
        return c
    def clean(self):
        d=super().clean()
        fields=['invoice_number','invoice_date','currency','net_amount','vat_amount','total_amount','po_number']
        for key in fields:
            if d.get(key) is None or d.get(key)=='':self.add_error(key,'Required before approval.')
        net,vat,total=d.get('net_amount'),d.get('vat_amount'),d.get('total_amount')
        if net is not None and vat is not None and total is not None:
            if abs(net+vat-total)>__import__('decimal').Decimal('0.02'):self.add_error('total_amount','Net + VAT must equal total within 0.02.')
        return d
