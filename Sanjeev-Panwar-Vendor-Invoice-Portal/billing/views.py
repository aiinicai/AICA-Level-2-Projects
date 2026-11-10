import fitz
from PIL import Image, UnidentifiedImageError
import csv,hashlib,io,re,uuid
from pathlib import Path
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse,Http404,HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.utils.text import get_valid_filename
from .models import Company,VendorProfile,Invoice,Document,ExportBatch,AuditEvent
from .forms import SignupForm,UploadForm,ReviewForm
from .extract import read_document,validate_recipient_pin,guess_fields,ExtractError
from django.conf import settings

MAX_TOTAL=20_000_000
ALLOWED={'.pdf','.jpg','.jpeg','.png'}
PRIVATE_DOCS=settings.DATA_DIR/'documents'
PRIVATE_DOCS.mkdir(parents=True,exist_ok=True)

def finance(user):return user.is_authenticated and user.is_staff
finance_required=user_passes_test(finance,login_url='/login/')
def audit(user,action,subject,details=''):
    AuditEvent.objects.create(user=user,action=action,subject=subject,details=details[:2000])

def home(request):
    if not request.user.is_authenticated:return render(request,'billing/welcome.html')
    if request.user.is_staff:return redirect('finance')
    profile=VendorProfile.objects.filter(user=request.user).first()
    invoices=Invoice.objects.filter(vendor=profile).select_related('company') if profile else Invoice.objects.none()
    return render(request,'billing/home.html',{'profile':profile,'invoices':invoices.order_by('-uploaded_at')[:100]})

def register(request):
    
    if request.user.is_authenticated:return redirect('home')
    form=SignupForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            u=User.objects.create_user(username=form.cleaned_data['email'],email=form.cleaned_data['email'],password=form.cleaned_data['password1'])
            VendorProfile.objects.create(user=u,legal_name=form.cleaned_data['legal_name'],kra_pin=form.cleaned_data['kra_pin'])
            audit(u,'VENDOR_REGISTERED',str(u.pk))
        login(request, u, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request,'Registration submitted. Finance approval is required before uploads are enabled.')
        return redirect('home')
    return render(request,'billing/register.html',{'form':form})

def valid_type(name,raw):
    ext=Path(name).suffix.lower()
    if ext not in ALLOWED:raise ExtractError('Only PDF, JPG and PNG are accepted.')
    ok=(ext=='.pdf' and raw.startswith(b'%PDF-')) or (ext=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ('.jpg','.jpeg') and raw.startswith(b'\xff\xd8\xff'))
    if not ok:raise ExtractError('File content does not match its PDF/JPG/PNG extension.')
    try:
        if ext == ".pdf":
            with fitz.open(stream=raw, filetype="pdf") as doc:
                if doc.needs_pass:
                    raise ExtractError(
                        "Password-protected PDFs are not accepted."
                    )
                if doc.page_count == 0 or doc.page_count > 50:
                    raise ExtractError(
                        "PDF must contain between 1 and 50 pages."
                    )
                if not doc.is_pdf:
                    raise ExtractError("Invalid PDF document.")

        else:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ("JPEG", "PNG"):
                    raise ExtractError("Invalid image format.")
                if image.width * image.height > 25_000_000:
                    raise ExtractError(
                        "Image resolution exceeds the permitted limit."
                    )
                image.verify()

    except ExtractError:
        raise
    except Exception:
        raise ExtractError(
            "The uploaded file is damaged or cannot be read."
        )


def file_input(f):
    if not f: return None
    if f.size>MAX_TOTAL:raise ExtractError('File exceeds the 20 MB submission maximum.')
    raw=f.read()
    valid_type(f.name,raw)
    return raw

@login_required
def upload(request):
    profile=VendorProfile.objects.filter(user=request.user).first()
    if request.user.is_staff: return redirect('finance')
    if profile is None or not profile.approved:
        messages.error(request,'Finance must approve your vendor account before you can upload invoices.')
        return redirect('home')
    form=UploadForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        invfile=form.cleaned_data['invoice'];pofile=form.cleaned_data['purchase_order'];support=form.cleaned_data['supporting_documents']
        files=[('INVOICE',invfile),('PO',pofile)]+([('SUPPORT',support)] if support else [])
        if sum(f.size for _,f in files)>MAX_TOTAL:
            form.add_error(None,'Combined invoice, PO and supporting documents exceed 20 MB.')
        else:
            try:
                raw_files=[(kind,f,file_input(f)) for kind,f in files]
                inv_text=read_document(raw_files[0][2],invfile.name)
                company=form.cleaned_data['company']
                validate_recipient_pin(inv_text,company)
                po_text=read_document(raw_files[1][2],pofile.name)
                extracted=guess_fields(inv_text)
                po_fields=guess_fields(po_text)
                if not extracted.get('po_number') and po_fields.get('po_number'):extracted['po_number']=po_fields['po_number']
                num=extracted.get('invoice_number','')
                if num and Invoice.objects.filter(vendor=profile,company=company,invoice_number__iexact=num).exclude(status=Invoice.Status.REJECTED).exists():
                    raise ExtractError('Possible duplicate: this vendor has already submitted the same invoice number to this company.')
                with transaction.atomic():
                    inv=Invoice.objects.create(reference='TEMP-'+uuid.uuid4().hex,company=company,vendor=profile,
                      vendor_notes=form.cleaned_data['vendor_notes'],extracted_text=inv_text[:50000],
                      extraction_notes='Initial local OCR is heuristic. Finance must verify every field.',**extracted)
                    inv.reference=f'{company.code}-{timezone.localdate():%Y}-{inv.pk:06d}'
                    inv.save(update_fields=['reference'])
                    for kind,f,raw in raw_files:
                        stored_name=uuid.uuid4().hex+Path(f.name).suffix.lower()
                        Document.objects.create(invoice=inv,kind=kind,original_name=Path(f.name).name[:255],stored_name=stored_name,byte_size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                    audit(request.user,'INVOICE_SUBMITTED',inv.reference)
                for kind,f,raw in raw_files:
                    # Safe private file storage with unguessable names, no web static serving.
                    doc=inv.documents.get(kind=kind)
                    (PRIVATE_DOCS/doc.stored_name).write_bytes(raw)
                send_mail('Vendor invoice received: '+inv.reference,
                  f'Reference: {inv.reference}\nCompany: {company.name}\nInvoice: {inv.invoice_number or "Pending verification"}\nCurrency: {inv.currency or "Pending verification"}\nTotal: {inv.total_amount if inv.total_amount is not None else "Pending verification"}\nStatus: Pending finance review\nContact: {settings.FINANCE_CONTACT_EMAIL}\nPlease notify finance of any extraction discrepancy.',
                  settings.DEFAULT_FROM_EMAIL,[request.user.email],fail_silently=True)
                messages.success(request,'Invoice accepted. Reference: '+inv.reference+'. Test email saved locally.')
                return redirect('invoice_detail',pk=inv.pk)
            except ExtractError as e:form.add_error(None,str(e))
            except Exception:
                form.add_error(
                    None,
                    "The document could not be processed. "
                    "Please contact Finance if the problem continues."
                )
    return render(request,'billing/upload.html',{'form':form,'max_mb':20})

@login_required
def invoice_detail(request,pk):
    inv=get_object_or_404(Invoice.objects.select_related('vendor__user','company'),pk=pk)
    if not request.user.is_staff and inv.vendor.user_id!=request.user.id:raise Http404
    return render(request,'billing/invoice_detail.html',{'inv':inv})

@login_required
def download_document(request,pk):
    doc=get_object_or_404(Document.objects.select_related('invoice__vendor'),pk=pk)
    if not request.user.is_staff and doc.invoice.vendor.user_id!=request.user.id:raise Http404
    path=PRIVATE_DOCS/doc.stored_name
    if not path.is_file():raise Http404
    safe=get_valid_filename(Path(doc.original_name).name)
    return FileResponse(open(path,'rb'),as_attachment=True,filename=safe)

@finance_required
def finance_dashboard(request):
    invoices=Invoice.objects.select_related('vendor','company').order_by('-uploaded_at')[:200]
    return render(request,'billing/finance.html',{'invoices':invoices,'pending_count':Invoice.objects.filter(status=Invoice.Status.REVIEW).count(),'vendor_count':VendorProfile.objects.filter(approved=False).count()})

@finance_required
def finance_vendors(request):
    vendors=VendorProfile.objects.select_related('user').order_by('approved','legal_name')
    return render(request,'billing/vendors.html',{'vendors':vendors})

@finance_required
def approve_vendor(request,pk):
    if request.method!='POST':return redirect('finance_vendors')
    v=get_object_or_404(VendorProfile,pk=pk)
    with transaction.atomic():
        v.approved=True;v.approved_by=request.user;v.approved_at=timezone.now();v.save()
        audit(request.user,'VENDOR_APPROVED',str(v.pk))
    messages.success(request,'Vendor approved: '+v.legal_name)
    return redirect('finance_vendors')

@finance_required
def finance_review(request,pk):
    inv=get_object_or_404(Invoice,pk=pk)
    if inv.status==Invoice.Status.EXPORTED:
        messages.error(request,'Already exported: changes are locked for this pilot.')
        return redirect('invoice_detail',pk=pk)
    form=ReviewForm(request.POST or None,instance=inv)
    if request.method=='POST':
        action=request.POST.get('action','save')
        if action=='reject':
            inv.finance_notes=request.POST.get('finance_notes','')[:2000];inv.status=Invoice.Status.REJECTED;inv.save(update_fields=['finance_notes','status'])
            audit(request.user,'INVOICE_REJECTED',inv.reference)
            messages.success(request,'Invoice rejected.');return redirect('finance')
        if form.is_valid():
            old=str({k:str(getattr(inv,k)) for k in form.fields})
            inv=form.save(commit=False)
            if action=='approve':
                if Invoice.objects.filter(vendor=inv.vendor,company=inv.company,invoice_number__iexact=inv.invoice_number,status__in=[Invoice.Status.APPROVED,Invoice.Status.EXPORTED]).exclude(pk=inv.pk).exists():
                    form.add_error('invoice_number','Another approved/exported invoice has this number for the same vendor and company.')
                else:
                    inv.status=Invoice.Status.APPROVED;inv.approved_at=timezone.now();inv.approved_by=request.user
            if not form.errors:
                inv.save()
                audit(request.user,'INVOICE_'+('APPROVED' if action=='approve' else 'EDITED'),inv.reference,'Previous: '+old)
                messages.success(request,'Invoice '+('approved.' if action=='approve' else 'saved.'))
                return redirect('finance')
    return render(request,'billing/review.html',{'inv':inv,'form':form})

def csv_safe(s):
    s='' if s is None else str(s)
    if s and s.lstrip().startswith(('=','+','-','@','\t','\r')):return "'"+s
    return s

@finance_required
def export_csv(request):
    if request.method!='POST':return redirect('finance')
    ids=list(Invoice.objects.filter(status=Invoice.Status.APPROVED).order_by('pk').values_list('pk',flat=True))
    if not ids:
        messages.info(request,'No approved invoices to export.');return redirect('finance')
    headers=['Submission_Reference','Company_Code','Company_PIN','Vendor_Name','Vendor_PIN','Invoice_Number','Invoice_Date','Upload_Date','Currency','Net_Amount','VAT_Amount','Gross_Amount','PO_Number','Finance_Status']
    buf=io.StringIO(newline='');writer=csv.writer(buf);writer.writerow(headers)
    with transaction.atomic():
        selected=list(Invoice.objects.select_related('company','vendor').filter(pk__in=ids,status=Invoice.Status.APPROVED).order_by('pk'))
        for inv in selected:
            writer.writerow([csv_safe(inv.reference),csv_safe(inv.company.code),csv_safe(inv.company.kra_pin),csv_safe(inv.vendor.legal_name),csv_safe(inv.vendor.kra_pin),csv_safe(inv.invoice_number),inv.invoice_date.isoformat() if inv.invoice_date else '',timezone.localtime(inv.uploaded_at).date().isoformat(),inv.currency,inv.net_amount,inv.vat_amount,inv.total_amount,csv_safe(inv.po_number),'Approved'])
        filename='erp_export_'+timezone.now().strftime('%Y%m%d_%H%M%S')+'.csv'
        batch=ExportBatch.objects.create(created_by=request.user,filename=filename,count=len(selected))
        Invoice.objects.filter(pk__in=[x.pk for x in selected]).update(status=Invoice.Status.EXPORTED,export_batch=batch)
        audit(request.user,'ERP_EXPORTED',str(batch.pk),str(len(selected))+' invoices')
    response=HttpResponse('\ufeff'+buf.getvalue(),content_type='text/csv; charset=utf-8')
    response['Content-Disposition']=f'attachment; filename="{filename}"'
    response['Cache-Control']='no-store'
    return response
