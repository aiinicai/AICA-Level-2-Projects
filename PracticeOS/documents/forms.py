import os

from django import forms
from django.conf import settings

from core.forms import TenantModelForm
from crm.models import Client

from .models import Document

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".txt", ".zip", ".json", ".xml"}


class DocumentForm(TenantModelForm):
    class Meta:
        model = Document
        fields = ["type", "client", "name", "file", "url", "physical_location", "financial_year", "category", "shared_with_client"]
        widgets = {"type": forms.RadioSelect, "category": forms.TextInput(attrs={"list": "doc-cats"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(firm=self.firm, is_active=True)
        self.fields["client"].empty_label = "Select client…"
        self.fields["file"].help_text = "PDF, images, Excel, Word, CSV, ZIP · max 20 MB"
        self.fields["name"].required = False
        self.fields["name"].help_text = "Optional for uploads: the file name is used if left blank."

    def clean(self):
        data = super().clean()
        kind = data.get("type")
        if kind == Document.Type.UPLOAD:
            f = data.get("file")
            if not f:
                self.add_error("file", "Choose a file to upload.")
            else:
                if os.path.splitext(f.name)[1].lower() not in ALLOWED_EXT:
                    self.add_error("file", "That file type isn't allowed.")
                elif f.size > settings.MAX_UPLOAD_BYTES:
                    self.add_error("file", "File is larger than 20 MB.")
            data["url"], data["physical_location"] = "", ""
        elif kind == Document.Type.LINK:
            if not data.get("url"):
                self.add_error("url", "Paste the link to the record.")
            data["file"], data["physical_location"] = None, ""
        elif kind == Document.Type.PHYSICAL:
            if not data.get("physical_location"):
                self.add_error("physical_location", "Say where the paper file is kept.")
            data["file"], data["url"] = None, ""
        if kind != Document.Type.UPLOAD and not data.get("name"):
            self.add_error("name", "Give this record a name.")
        return data

    def save(self, commit=True):
        doc = super().save(commit=False)
        f = self.cleaned_data.get("file")
        if doc.type == Document.Type.UPLOAD and f:
            doc.name = doc.name or f.name
            doc.mime_type = getattr(f, "content_type", "") or ""
            doc.size_bytes = f.size
        if commit:
            doc.save()
        return doc
