from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from app.decorators.decorators import role_required_any
from app.decorators.features import feature_required
from app.forms.library import LibraryBookForm, LibraryCopyForm, LibraryIssueForm, LibraryLostForm, LibraryReturnForm
from app.models import LibraryBook, LibraryCategory, LibraryCopy, LibraryFine, LibraryLoan, Staff, Student
from app.services.library import CirculationError, issue_copy, mark_loan_lost, renew_loan, resolve_fine, return_loan


LIBRARY_ROLES = ("Admin", "Librarian", "Library Assistant", "Head Teacher", "Head master")


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_dashboard(request):
    now = timezone.now()
    today = timezone.localdate()
    active_loans = LibraryLoan.objects.filter(returned_at__isnull=True)
    overdue_qs = active_loans.filter(due_at__lt=now).select_related("copy__book", "student", "staff")
    overdue_attention = list(overdue_qs.order_by("due_at")[:6])
    for loan in overdue_attention:
        loan.days_overdue = max(1, (today - timezone.localtime(loan.due_at).date()).days)
    activity = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        issued = LibraryLoan.objects.filter(issued_at__date=day).count()
        returned = LibraryLoan.objects.filter(returned_at__date=day).count()
        activity.append({"date": day, "issued": issued, "returned": returned})
    activity_peak = max([row["issued"] for row in activity] + [row["returned"] for row in activity] + [1])
    for row in activity:
        row["issued_height"] = max(4, round(row["issued"] * 100 / activity_peak))
        row["returned_height"] = max(4, round(row["returned"] * 100 / activity_peak))
    copies = LibraryCopy.objects.count()
    available = LibraryCopy.objects.filter(status=LibraryCopy.STATUS_AVAILABLE).count()
    context = {
        "titles": LibraryBook.objects.count(), "copies": copies, "available": available,
        "availability_percent": round((available / copies) * 100) if copies else 0,
        "active_loans": active_loans.count(), "overdue": overdue_qs.count(),
        "due_today": active_loans.filter(due_at__date=today).count(),
        "issued_today": LibraryLoan.objects.filter(issued_at__date=today).count(),
        "returned_today": LibraryLoan.objects.filter(returned_at__date=today).count(),
        "outstanding_fines": LibraryFine.objects.filter(status=LibraryFine.STATUS_OUTSTANDING).count(),
        "overdue_attention": overdue_attention, "activity": activity,
        "popular_books": LibraryBook.objects.annotate(issue_count=Count("copies__loans")).filter(
            issue_count__gt=0
        ).order_by("-issue_count", "title")[:5],
        "today": today,
    }
    return render(request, "library/dashboard.html", context)


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_catalogue(request):
    books = LibraryBook.objects.select_related("category").annotate(
        copy_count=Count("copies", distinct=True),
        available_count=Count("copies", filter=Q(copies__status="available"), distinct=True),
    )
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    availability = request.GET.get("availability", "").strip()
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(isbn__icontains=query) | Q(author__icontains=query)
            | Q(copies__barcode__icontains=query) | Q(copies__accession_number__icontains=query)
        ).distinct()
    if category.isdigit():
        books = books.filter(category_id=int(category))
    if availability == "available":
        books = books.filter(available_count__gt=0)
    elif availability == "unavailable":
        books = books.filter(available_count=0)
    return render(request, "library/catalogue.html", {
        "books": books.order_by("title"), "query": query, "categories": LibraryCategory.objects.order_by("name"),
        "selected_category": category, "selected_availability": availability,
    })


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_book_create(request):
    form = LibraryBookForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        book = form.save()
        messages.success(request, "Book title added.")
        return redirect("library_book_detail", book_id=book.pk)
    return render(request, "library/form.html", {"form": form, "title": "Add book title"})


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_book_detail(request, book_id):
    book = get_object_or_404(LibraryBook.objects.prefetch_related("copies"), pk=book_id)
    copies = book.copies.all()
    history = LibraryLoan.objects.filter(copy__book=book).select_related("copy", "student", "staff").order_by("-issued_at")[:10]
    return render(request, "library/book_detail.html", {
        "book": book, "copy_count": copies.count(),
        "available_count": copies.filter(status=LibraryCopy.STATUS_AVAILABLE).count(),
        "issued_count": copies.filter(status=LibraryCopy.STATUS_ON_LOAN).count(), "history": history,
    })


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_copy_create(request, book_id):
    book = get_object_or_404(LibraryBook, pk=book_id)
    form = LibraryCopyForm(request.POST or None, initial={"book": book})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Physical copy added.")
        return redirect("library_book_detail", book_id=book.pk)
    return render(request, "library/form.html", {"form": form, "title": f"Add copy — {book.title}"})


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_issue(request):
    form = LibraryIssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            student = form.cleaned_data.get("student")
            staff = form.cleaned_data.get("staff")
            loan = issue_copy(
                copy_id=form.cleaned_data["copy"].pk, actor=request.user,
                student_id=student.pk if student else None, staff_id=staff.pk if staff else None,
            )
            messages.success(request, f"Issued until {loan.due_at:%d %b %Y}.")
            return redirect("library_dashboard")
        except (CirculationError, Student.DoesNotExist, Staff.DoesNotExist) as exc:
            form.add_error(None, str(exc))
    return render(request, "library/issue.html", {"form": form})


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_loans(request):
    loans = LibraryLoan.objects.select_related("copy__book", "student", "staff").filter(returned_at__isnull=True)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active")
    if query:
        loans = loans.filter(
            Q(copy__barcode__icontains=query) | Q(copy__accession_number__icontains=query)
            | Q(copy__book__title__icontains=query) | Q(student__student_name__icontains=query)
            | Q(student__reg_no__icontains=query) | Q(staff__first_name__icontains=query)
            | Q(staff__last_name__icontains=query)
        )
    if status == "overdue":
        loans = loans.filter(due_at__lt=timezone.now())
    elif status == "due_today":
        loans = loans.filter(due_at__date=timezone.localdate())
    return render(request, "library/loans.html", {
        "loans": loans.order_by("due_at"), "now": timezone.now(), "query": query, "selected_status": status,
    })


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_members(request):
    query = request.GET.get("q", "").strip()
    students = Student.objects.filter(is_active=True).select_related("current_class", "stream").annotate(
        active_loan_count=Count("library_loans", filter=Q(library_loans__returned_at__isnull=True), distinct=True),
        overdue_count=Count("library_loans", filter=Q(library_loans__returned_at__isnull=True, library_loans__due_at__lt=timezone.now()), distinct=True),
    )
    staff = Staff.objects.filter(staff_status="Active").annotate(
        active_loan_count=Count("library_loans", filter=Q(library_loans__returned_at__isnull=True), distinct=True),
        overdue_count=Count("library_loans", filter=Q(library_loans__returned_at__isnull=True, library_loans__due_at__lt=timezone.now()), distinct=True),
    )
    if query:
        students = students.filter(Q(student_name__icontains=query) | Q(reg_no__icontains=query) | Q(contact__icontains=query))
        staff = staff.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(contacts__icontains=query))
    return render(request, "library/members.html", {
        "students": students.order_by("student_name")[:100], "staff_members": staff.order_by("first_name", "last_name")[:100],
        "query": query,
    })


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_return(request, loan_id):
    if request.method == "POST":
        form = LibraryReturnForm(request.POST)
        if form.is_valid():
            try:
                return_loan(
                    loan_id=loan_id, actor=request.user, condition=form.cleaned_data["condition"],
                    damage_amount=form.cleaned_data.get("damage_amount") or 0, notes=form.cleaned_data.get("notes", ""),
                )
                messages.success(request, "Book returned and any applicable library fine was recorded.")
            except (CirculationError, LibraryLoan.DoesNotExist) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Return not recorded: " + " ".join(error for errors in form.errors.values() for error in errors))
    return redirect("library_loans")


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_renew(request, loan_id):
    if request.method == "POST":
        try:
            renew_loan(loan_id=loan_id, actor=request.user)
            messages.success(request, "Loan renewed.")
        except CirculationError as exc:
            messages.error(request, str(exc))
    return redirect("library_loans")


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_mark_lost(request, loan_id):
    if request.method == "POST":
        form = LibraryLostForm(request.POST)
        if form.is_valid():
            try:
                mark_loan_lost(
                    loan_id=loan_id, actor=request.user, amount=form.cleaned_data["amount"],
                    notes=form.cleaned_data.get("notes", ""),
                )
                messages.success(request, "The copy was marked lost and the library charge recorded.")
            except (CirculationError, LibraryLoan.DoesNotExist) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Lost-item action not recorded. Enter a valid non-negative replacement charge.")
    return redirect("library_loans")


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_fines(request):
    fines = LibraryFine.objects.select_related(
        "loan__copy__book", "loan__student", "loan__staff", "assessed_by", "resolved_by"
    )
    status = request.GET.get("status", "outstanding")
    if status in dict(LibraryFine.STATUS_CHOICES):
        fines = fines.filter(status=status)
    return render(request, "library/fines.html", {"fines": fines, "selected_status": status})


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_fine_resolve(request, fine_id):
    if request.method == "POST":
        try:
            resolve_fine(fine_id=fine_id, actor=request.user, resolution=request.POST.get("resolution", ""))
            messages.success(request, "Library fine updated.")
        except (CirculationError, LibraryFine.DoesNotExist) as exc:
            messages.error(request, str(exc))
    return redirect("library_fines")
