import re
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from tracker.models import (
    User, Client, ClientContact, Staff, Engagement, EngagementTeam,
    Query, QueryResponse, Attachment, ExceptionApproval, Memo
)


def validate_strong_password(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain at least one digit (0-9).")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character (!@#$%^&* etc.).")


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Official Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@firm.com or contact@client.com', 'autofocus': True})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'})
    )


class ForcePasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        label="New Secure Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min 8 chars, 1 uppercase, 1 digit, 1 special char'}),
        validators=[validate_strong_password]
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise ValidationError("New passwords do not match.")
        return cleaned_data


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'client_code', 'client_name', 'group_name', 'constitution',
            'industry', 'registered_address', 'city', 'state',
            'financial_year_end', 'listed_status', 'risk_category',
            'client_since', 'status', 'remarks'
        ]
        widgets = {
            'client_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CL001'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'group_name': forms.TextInput(attrs={'class': 'form-control'}),
            'constitution': forms.Select(attrs={'class': 'form-select'}),
            'industry': forms.Select(attrs={'class': 'form-select'}),
            'registered_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'financial_year_end': forms.TextInput(attrs={'class': 'form-control'}),
            'listed_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'risk_category': forms.Select(attrs={'class': 'form-select'}),
            'client_since': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ClientContactForm(forms.ModelForm):
    create_user_account = forms.BooleanField(
        required=False,
        initial=True,
        label="Provision Client Portal Login Account",
        help_text="Generates client portal user with temporary password (Client@123)"
    )

    class Meta:
        model = ClientContact
        fields = ['contact_name', 'designation', 'email', 'mobile', 'is_primary_coordinator', 'status']
        widgets = {
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Anand Shah'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CFO / Accounts Head'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. cfo@client.com'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
            'is_primary_coordinator': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class StaffForm(forms.ModelForm):
    create_user_account = forms.BooleanField(
        required=False,
        initial=True,
        label="Provision Staff Login Account",
        help_text="Creates staff login with default credentials"
    )

    class Meta:
        model = Staff
        fields = ['staff_code', 'full_name', 'email', 'designation', 'membership_no', 'date_of_joining', 'reporting_to', 'status']
        widgets = {
            'staff_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP001'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'membership_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 504123'}),
            'date_of_joining': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reporting_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        staff_instance = self.instance
        
        # FR-3: Deactivation blocked if staff member is the only active Partner on any live engagement
        if status == 'Inactive' and staff_instance.pk and staff_instance.designation == 'Partner':
            live_engagements = Engagement.objects.filter(
                status__in=['Planned', 'In Progress'],
                team_members__staff=staff_instance,
                team_members__role_on_engagement='Partner',
                team_members__is_active=True
            ).distinct()
            
            for eng in live_engagements:
                other_partners = eng.team_members.filter(
                    role_on_engagement='Partner',
                    is_active=True
                ).exclude(staff=staff_instance).count()
                
                if other_partners == 0:
                    raise ValidationError(
                        f"Cannot deactivate {staff_instance.full_name}: They are the sole active Partner on live engagement '{eng.engagement_code}'. Please reassign a Partner first."
                    )
        return cleaned_data


class EngagementForm(forms.ModelForm):
    class Meta:
        model = Engagement
        fields = [
            'client', 'financial_year', 'audit_type', 'period_from',
            'period_to', 'planned_start', 'target_completion', 'status',
            'client_coordinator_review_enabled'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'financial_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2025-26'}),
            'audit_type': forms.Select(attrs={'class': 'form-select'}),
            'period_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'period_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'planned_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'target_completion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'client_coordinator_review_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get('client')
        fy = cleaned_data.get('financial_year')
        audit_type = cleaned_data.get('audit_type')
        
        if client and fy and audit_type:
            qs = Engagement.objects.filter(client=client, financial_year=fy, audit_type=audit_type)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"An engagement for {client.client_name} ({fy} - {audit_type}) already exists.")
        return cleaned_data


class EngagementTeamForm(forms.ModelForm):
    class Meta:
        model = EngagementTeam
        fields = ['staff', 'role_on_engagement', 'is_reviewer', 'assigned_on', 'is_active', 'independence_declared']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'role_on_engagement': forms.Select(attrs={'class': 'form-select'}),
            'is_reviewer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assigned_on': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'independence_declared': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['is_active'].initial = True

    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        role = cleaned_data.get('role_on_engagement')
        is_active = cleaned_data.get('is_active')
        engagement = self.instance.engagement if self.instance.pk else None

        if staff and role and is_active:
            # Rule: Article Assistant cannot hold Manager or Partner role
            if staff.designation == 'Article Assistant' and role in ['Partner', 'Manager']:
                raise ValidationError(f"{staff.full_name} is an Article Assistant and cannot be assigned as a {role}.")

            # Rule: The same staff member cannot hold two active roles on one engagement
            if engagement:
                existing = EngagementTeam.objects.filter(
                    engagement=engagement,
                    staff=staff,
                    is_active=True
                )
                if self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)
                if existing.exists():
                    raise ValidationError(f"{staff.full_name} is already assigned with an active role on this engagement.")
        return cleaned_data


class QueryForm(forms.ModelForm):
    attachment = forms.FileField(required=False, label="Upload Supporting Document (PDF, DOCX, XLSX, PNG, JPG; Max 10MB)", widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Query
        fields = [
            'engagement', 'query_type', 'area', 'title', 'description',
            'document_requested', 'amount_involved', 'priority', 'risk_rating',
            'assigned_to_client_contact', 'due_date', 'is_repeat_observation',
            'prior_year_query_ref', 'carry_to_memo',
            'condition', 'criteria', 'cause', 'effect_risk', 'recommendation'
        ]
        widgets = {
            'engagement': forms.Select(attrs={'class': 'form-select'}),
            'query_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_query_type'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief informative summary'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'document_requested': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List specific vouchers, reconciliations, or registers needed'}),
            'amount_involved': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '₹ 0.00'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'risk_rating': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to_client_contact': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_repeat_observation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prior_year_query_ref': forms.Select(attrs={'class': 'form-select'}),
            'carry_to_memo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # 5-element fields
            'condition': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'What was found during testing / audit variance'}),
            'criteria': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Standard / Policy / Regulatory requirement'}),
            'cause': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Why did this breakdown occur (root cause)'}),
            'effect_risk': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Potential financial / compliance risk exposure'}),
            'recommendation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Actionable remediation recommendation'}),
        }

    def clean_attachment(self):
        file = self.cleaned_data.get('attachment')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size exceeds 10MB maximum limit.")
            allowed_exts = ['pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'csv']
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed_exts:
                raise ValidationError(f"File format '.{ext}' is not supported. Allowed formats: {', '.join(allowed_exts)}.")
        return file


class QueryResponseForm(forms.Form):
    response_text = forms.CharField(
        label="Response / Management Explanation",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Type your response, clarification, or remediation notes here...'})
    )
    attachment = forms.FileField(
        required=False,
        label="Attach Document (Optional)",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean_attachment(self):
        file = self.cleaned_data.get('attachment')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size exceeds 10MB maximum limit.")
            allowed_exts = ['pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'csv']
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed_exts:
                raise ValidationError(f"File format '.{ext}' is not supported. Allowed formats: {', '.join(allowed_exts)}.")
        return file


class ExceptionRequestForm(forms.ModelForm):
    class Meta:
        model = ExceptionApproval
        fields = ['exception_type', 'query', 'justification']
        widgets = {
            'exception_type': forms.Select(attrs={'class': 'form-select'}),
            'query': forms.Select(attrs={'class': 'form-select'}),
            'justification': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide detailed business/audit justification (Minimum 100 characters required)...'
            }),
        }

    def clean_justification(self):
        justification = self.cleaned_data.get('justification', '').strip()
        if len(justification) < 100:
            raise ValidationError(f"Justification must be at least 100 characters long (currently {len(justification)} characters).")
        return justification


class ExceptionDecisionForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[('Approved', 'Approve Exception'), ('Rejected', 'Reject Exception')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    partner_remarks = forms.CharField(
        label="Partner Remarks / Directives (Mandatory)",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter audit partner comments, scope considerations, or risk assessment...'})
    )
    password = forms.CharField(
        label="Step-Up Authentication: Re-enter Your Partner Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your login password to authorize this action'}),
        help_text="Step-up authentication ensures non-repudiation for formal partner exception approvals."
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        if not self.user or not self.user.check_password(pwd):
            raise ValidationError("Incorrect password. Step-up authentication failed.")
        return pwd


class StepUpAuthForm(forms.Form):
    password = forms.CharField(
        label="Step-Up Authentication: Re-enter Your Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password to authorize'}),
        help_text="Re-authenticate to execute sign-off and locking."
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        if not self.user or not self.user.check_password(pwd):
            raise ValidationError("Incorrect password. Step-up authentication failed.")
        return pwd
