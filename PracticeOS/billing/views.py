import re
from datetime import date
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import any_role_required, staff_required
from core.utils import firm_object_or_404
from crm.models import Client

from .forms import FromTimeForm, InvoiceForm, ItemForm, PaymentForm, TimeEntryForm
from .models import Invoice, TimeEntry
from .services import cancel_invoice, create_invoice, record_payment

ItemFormSet = formset_factory(ItemForm, extra=2, min_num=1, validate_min=True)


# ── Timesheets ──


def _parse_date(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


@staff_required
def time_list(request):
    today = timezone.localdate()
    start = _parse_date(request.GET.get("from"), today.replace(day=1))
    end = _parse_date(request.GET.get("to"), today)
    client_id = request.GET.get("client", "")

    entries = TimeEntry.objects.filter(firm=request.firm, work_date__range=(start, end)).select_related("client", "task", "user")
    if not request.user.is_admin:  # team members only ever see their own time
        entries = entries.filter(user=request.user)
    if client_id.isdigit():
        entries = entries.filter(client_id=client_id)

    summary = [
        {"client": row["client__name"], "minutes": row["total"]}
        for row in entries.order_by().values("client__name").annotate(total=Sum("minutes")).order_by("client__name")
    ]
    billable = sum(e.minutes for e in entries if e.billable)
    total = sum(e.minutes for e in entries)
    return render(request, "billing/time_list.html", {
        "entries": entries, "summary": summary, "total": total, "billable": billable,
        "clients": Client.objects.filter(firm=request.firm), "f": {"from": start.isoformat(), "to": end.isoformat(), "client": client_id},
    })


def _editable_entry(request, pk):
    entry = firm_object_or_404(TimeEntry, request, pk=pk)
    if not request.user.is_admin and entry.user_id != request.user.pk:
        raise PermissionDenied
    return entry


@staff_required
def time_form(request, pk=None):
    entry = _editable_entry(request, pk) if pk else None
    if entry and entry.invoice_id:
        messages.error(request, "That entry has already been invoiced.")
        return redirect("time_list")
    form = TimeEntryForm(request.POST or None, instance=entry, firm=request.firm)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not entry:
            obj.user = request.user
        obj.save()
        messages.success(request, "Time saved.")
        return redirect("time_list")
    return render(request, "form.html", {"form": form, "title": "Edit time entry" if entry else "Log time", "cancel_url": "time_list",
                                         "delete_url": "time_delete" if entry else None, "delete_pk": pk})


@staff_required
@require_POST
def time_delete(request, pk):
    entry = _editable_entry(request, pk)
    if entry.invoice_id:
        messages.error(request, "That entry has already been invoiced.")
    else:
        entry.delete()
        messages.success(request, "Time entry deleted.")
    return redirect("time_list")


# ── Invoices ──


@staff_required
def invoice_list(request):
    invoices = Invoice.objects.filter(firm=request.firm).select_related("client").prefetch_related("payments")
    status, client_id = request.GET.get("status", ""), request.GET.get("client", "")
    if status in Invoice.Status.values:
        invoices = invoices.filter(status=status)
    if client_id.isdigit():
        invoices = invoices.filter(client_id=client_id)
    invoices = list(invoices)
    pending = [i for i in invoices if i.status == Invoice.Status.PENDING]
    return render(request, "billing/invoice_list.html", {
        "invoices": invoices, "status": status, "client_id": client_id, "clients": Client.objects.filter(firm=request.firm),
        "pending_total": sum(i.balance for i in pending), "overdue_total": sum(i.balance for i in pending if i.is_overdue),
        "statuses": Invoice.Status.choices,
    })


@staff_required
def invoice_create(request):
    form = InvoiceForm(request.POST or None, firm=request.firm, initial={"client": request.GET.get("client")})
    formset = ItemFormSet(request.POST or None, prefix="items")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        items = [f.cleaned_data for f in formset if f.cleaned_data]
        try:
            invoice = create_invoice(firm=request.firm, client=form.cleaned_data["client"], items=items, issue_date=form.cleaned_data["issue_date"],
                                     due_date=form.cleaned_data["due_date"], notes=form.cleaned_data["notes"])
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, f"Invoice {invoice.number} created.")
            return redirect("invoice_detail", pk=invoice.pk)
    return render(request, "billing/invoice_form.html", {"form": form, "formset": formset})


@staff_required
def invoice_from_time(request):
    client = None
    client_id = request.GET.get("client", "")
    if client_id.isdigit():
        client = Client.objects.filter(firm=request.firm, pk=client_id).first()
    form = FromTimeForm(request.POST or None, firm=request.firm, client=client) if client else None
    if client and request.method == "POST" and form.is_valid():
        try:
            invoice = create_invoice(firm=request.firm, client=client, items=form.items(), due_date=form.cleaned_data["due_date"], time_entries=form.cleaned_data["entries"])
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, f"Invoice {invoice.number} created from {len(form.cleaned_data['entries'])} time entries.")
            return redirect("invoice_detail", pk=invoice.pk)
    return render(request, "billing/invoice_from_time.html", {"clients": Client.objects.filter(firm=request.firm, is_active=True), "client": client, "form": form})


def _clean_phone_for_whatsapp(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"91{digits[1:]}"
    return digits


def _build_invoice_summary_text(invoice, firm, invoice_url):
    client = invoice.client
    lines = [
        f"Dear {client.name},",
        "",
        f"Greetings from *{firm.name}*.",
        f"Please find below the summary for Invoice *{invoice.number}*:",
        "",
        f"📄 *Invoice No:* {invoice.number}",
        f"📅 *Issue Date:* {invoice.issue_date.strftime('%d-%b-%Y')}",
        f"⏳ *Due Date:* {invoice.due_date.strftime('%d-%b-%Y')}",
        f"💰 *Total Amount:* ₹{invoice.total:,.2f}",
    ]
    if invoice.paid_amount > 0:
        lines.append(f"✅ *Amount Received:* ₹{invoice.paid_amount:,.2f}")
    lines.append(f"⚠️ *Balance Payable:* ₹{invoice.balance:,.2f}")

    if firm.bank_name or firm.upi_id:
        lines.append("")
        lines.append("🏦 *Bank & Payment Details:*")
        if firm.bank_name:
            lines.append(f"• Bank: {firm.bank_name}")
        if firm.bank_account_name:
            lines.append(f"• A/C Name: {firm.bank_account_name}")
        if firm.bank_account_no:
            lines.append(f"• A/C No: {firm.bank_account_no}")
        if firm.bank_ifsc:
            lines.append(f"• IFSC: {firm.bank_ifsc}")
        if firm.bank_branch:
            lines.append(f"• Branch: {firm.bank_branch}")
        if firm.upi_id:
            lines.append(f"• UPI ID: {firm.upi_id}")

    lines.append("")
    lines.append("🔗 *View & Print Invoice Online:*")
    lines.append(invoice_url)
    lines.append("")
    lines.append(f"Thank you,\n*{firm.name}*")
    return "\n".join(lines)


@any_role_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("client").prefetch_related("items", "payments"),
        firm=request.firm,
        pk=pk
    )
    if request.user.is_client and invoice.client_id != request.user.client_id:
        raise PermissionDenied

    invoice_url = request.build_absolute_uri(request.path)
    wa_message = _build_invoice_summary_text(invoice, request.firm, invoice_url)
    wa_phone = _clean_phone_for_whatsapp(invoice.client.phone)
    wa_url = f"https://api.whatsapp.com/send?phone={wa_phone}&text={quote(wa_message)}" if wa_phone else f"https://api.whatsapp.com/send?text={quote(wa_message)}"

    email_subject = f"Tax Invoice {invoice.number} from {request.firm.name}"
    mailto_url = f"mailto:{invoice.client.email or ''}?subject={quote(email_subject)}&body={quote(wa_message)}"

    return render(request, "billing/invoice_detail.html", {
        "invoice": invoice,
        "wa_url": wa_url,
        "wa_message": wa_message,
        "wa_phone": wa_phone,
        "mailto_url": mailto_url,
        "email_subject": email_subject,
    })


@staff_required
@require_POST
def invoice_send_email(request, pk):
    invoice = firm_object_or_404(
        Invoice.objects.select_related("client").prefetch_related("items"),
        request,
        pk=pk
    )
    recipient = (request.POST.get("recipient") or invoice.client.email or "").strip()
    if not recipient:
        messages.error(request, "Please enter a recipient email address.")
        return redirect("invoice_detail", pk=pk)

    custom_note = request.POST.get("custom_note", "").strip()
    firm = request.firm
    invoice_url = request.build_absolute_uri(f"/invoices/{invoice.pk}/")
    subject = f"Tax Invoice {invoice.number} from {firm.name}"

    context = {
        "invoice": invoice,
        "firm": firm,
        "client": invoice.client,
        "custom_note": custom_note,
        "invoice_url": invoice_url,
    }

    html_content = render_to_string("emails/invoice_email.html", context)
    text_content = _build_invoice_summary_text(invoice, firm, invoice_url)
    if custom_note:
        text_content = f"Note from {firm.name}:\n{custom_note}\n\n" + text_content

    from_email = settings.DEFAULT_FROM_EMAIL
    if firm.email:
        from_email = f"{firm.name} <{firm.email}>"

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        messages.success(request, f"Invoice {invoice.number} successfully emailed to {recipient}.")
    except Exception as e:
        messages.warning(
            request,
            f"Email could not be delivered directly by server ({e}). You can use the 'Open in Email App' button to send via your Outlook or Gmail."
        )

    return redirect("invoice_detail", pk=pk)


@staff_required
def invoice_pay(request, pk):
    invoice = firm_object_or_404(Invoice, request, pk=pk)
    if invoice.status != Invoice.Status.PENDING:
        messages.error(request, "Only pending invoices can receive payments.")
        return redirect("invoice_detail", pk=pk)
    form = PaymentForm(request.POST or None, invoice=invoice)
    if request.method == "POST" and form.is_valid():
        try:
            record_payment(invoice, **form.cleaned_data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Payment recorded.")
            return redirect("invoice_detail", pk=pk)
    return render(request, "form.html", {"form": form, "title": f"Record payment – {invoice.number}", "cancel_url": "invoice_detail", "back_pk": pk,
                                         "intro": f"{invoice.client.name} · balance ₹{invoice.balance}. Entering the full balance marks the invoice as Paid; a smaller amount records a part payment.",
                                         "submit": "Record payment"})


@staff_required
@require_POST
def invoice_cancel(request, pk):
    invoice = firm_object_or_404(Invoice, request, pk=pk)
    try:
        cancel_invoice(invoice)
        messages.success(request, f"{invoice.number} cancelled. Its number is retained for audit.")
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    return redirect("invoice_detail", pk=pk)
