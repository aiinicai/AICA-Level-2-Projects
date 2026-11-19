import json

from django.contrib import messages
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.decorators import staff_required
from core.utils import firm_object_or_404

from .forms import RuleForm, TaskForm
from .models import RecurringRule, Task
from .recurrence import PRESETS, generate_due_tasks


@staff_required
def board(request):
    mine = request.GET.get("mine") == "1"
    tasks = Task.objects.filter(firm=request.firm).select_related("client", "assignee")
    if mine:
        tasks = tasks.filter(assignee=request.user)
    tasks = tasks.order_by(F("due_date").asc(nulls_last=True), "-created_at")
    columns = [(value, label, [t for t in tasks if t.status == value]) for value, label in Task.Status.choices]
    return render(request, "workflow/board.html", {"columns": columns, "mine": mine})


@staff_required
def task_form(request, pk=None):
    task = firm_object_or_404(Task, request, pk=pk) if pk else None
    form = TaskForm(request.POST or None, instance=task, firm=request.firm, initial={"client": request.GET.get("client")} if not task else None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not task:
            obj.created_by = request.user
        obj.save()
        messages.success(request, "Task saved.")
        return redirect("board")
    return render(request, "form.html", {"form": form, "title": "Edit task" if task else "New task", "cancel_url": "board",
                                         "delete_url": "task_delete" if task else None, "delete_pk": pk})


@staff_required
@require_POST
def task_delete(request, pk):
    firm_object_or_404(Task, request, pk=pk).delete()
    messages.success(request, "Task deleted.")
    return redirect("board")


@staff_required
@require_POST
def task_status(request, pk):
    """Called by the Kanban drag & drop (fetch + CSRF header)."""
    task = firm_object_or_404(Task, request, pk=pk)
    try:
        status = json.loads(request.body).get("status")
    except (ValueError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if status not in Task.Status.values:
        return JsonResponse({"error": "Invalid status"}, status=400)
    task.status = status
    task.save()
    return JsonResponse({"ok": True, "status": task.status})


# ── Recurring deadlines ──


@staff_required
def recurring_list(request):
    rules = RecurringRule.objects.filter(firm=request.firm).select_related("client")
    return render(request, "workflow/recurring_list.html", {"rules": rules})


@staff_required
def recurring_create(request):
    form = RuleForm(request.POST or None, firm=request.firm)
    if request.method == "POST" and form.is_valid():
        form.save()
        result = generate_due_tasks(request.firm)  # release anything already inside its lead window
        messages.success(request, f"Schedule created. {result['tasks_created']} task(s) generated now.")
        return redirect("recurring_list")
    return render(request, "workflow/recurring_form.html", {"form": form, "presets": PRESETS})


@staff_required
@require_POST
def recurring_toggle(request, pk):
    rule = firm_object_or_404(RecurringRule, request, pk=pk)
    rule.is_active = not rule.is_active
    rule.save(update_fields=["is_active"])
    return redirect("recurring_list")


@staff_required
@require_POST
def recurring_delete(request, pk):
    firm_object_or_404(RecurringRule, request, pk=pk).delete()  # tasks already created are kept (SET_NULL)
    messages.success(request, "Schedule deleted. Tasks already created were kept.")
    return redirect("recurring_list")


@staff_required
@require_POST
def recurring_run(request):
    result = generate_due_tasks(request.firm)
    messages.success(request, f"{result['tasks_created']} task(s) created from {result['rules_checked']} schedule(s).")
    return redirect("recurring_list")
