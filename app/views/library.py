from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from app.decorators.decorators import role_required_any
from app.decorators.features import feature_required
from app.forms.library import LibraryBookForm, LibraryCopyForm, LibraryIssueForm, LibraryLostForm, LibraryReturnForm
from app.models import LibraryBook, LibraryCopy, LibraryFine, LibraryLoan, Staff, Student
from app.services.library import CirculationError, issue_copy, mark_loan_lost, renew_loan, resolve_fine, return_loan


LIBRARY_ROLES = ("Admin", "Librarian", "Library Assistant", "Head Teacher", "Head master")


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_dashboard(request):
    context = {
        "titles": LibraryBook.objects.count(), "copies": LibraryCopy.objects.count(),
        "available": LibraryCopy.objects.filter(status="available").count(),
        "active_loans": LibraryLoan.objects.filter(returned_at__isnull=True).count(),
        "overdue": LibraryLoan.objects.filter(returned_at__isnull=True, due_at__lt=timezone.now()).count(),
        "outstanding_fines": LibraryFine.objects.filter(status=LibraryFine.STATUS_OUTSTANDING).count(),
        "recent_loans": LibraryLoan.objects.select_related("copy__book", "student", "staff")[:10],
    }
    return render(request, "library/dashboard.html", context)


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_catalogue(request):
    books = LibraryBook.objects.annotate(copy_count=Count("copies"), available_count=Count("copies", filter=Q(copies__status="available")))
    query = request.GET.get("q", "").strip()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(isbn__icontains=query) | Q(author__icontains=query))
    return render(request, "library/catalogue.html", {"books": books, "query": query})


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
    return render(request, "library/book_detail.html", {"book": book})


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
            loan = issue_copy(copy_id=form.cleaned_data["copy"].pk, actor=request.user, student_id=form.cleaned_data.get("student_id"), staff_id=form.cleaned_data.get("staff_id"))
            messages.success(request, f"Issued until {loan.due_at:%d %b %Y}.")
            return redirect("library_dashboard")
        except (CirculationError, Student.DoesNotExist, Staff.DoesNotExist) as exc:
            form.add_error(None, str(exc))
    return render(request, "library/issue.html", {"form": form})


@feature_required("LIBRARY_ENABLED")
@role_required_any(*LIBRARY_ROLES)
def library_loans(request):
    loans = LibraryLoan.objects.select_related("copy__book", "student", "staff").filter(returned_at__isnull=True)
    return render(request, "library/loans.html", {"loans": loans, "now": timezone.now()})


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
