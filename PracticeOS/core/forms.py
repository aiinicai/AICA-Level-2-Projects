from django import forms


def date_input():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class StyledFormMixin:
    """Gives every widget the Tailwind classes used by the templates."""

    def style_widgets(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "h-4 w-4 rounded border-slate-300")
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                continue
            else:
                widget.attrs.setdefault("class", "input")
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)


class TenantModelForm(StyledFormMixin, forms.ModelForm):
    """ModelForm bound to a firm. Every foreign-key dropdown is narrowed to that firm's records
    (so a forged id for another tenant's client/user fails validation) and the saved row is
    stamped with the firm."""

    def __init__(self, *args, firm, **kwargs):
        super().__init__(*args, **kwargs)
        self.firm = firm
        self.instance.firm = firm
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField) and hasattr(field.queryset.model, "firm_id"):
                field.queryset = field.queryset.filter(firm=firm)
        self.style_widgets()
