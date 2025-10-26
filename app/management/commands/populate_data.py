from django.core.management.base import BaseCommand
from faker import Faker
import random
from app.models import (
    Currency, AcademicYear, Section, Signature, Department,
    Role, Staff, BankDetail, StaffDocument,
    Classroom, TimeSlot, BreakPeriod, Timetable,
    BankAccount, Vendor, Expense, Budget, BudgetItem, Expenditure, ExpenditureItem,
    IncomeSource, Transaction, BankStatement, BankTransaction, CashFlowStatement,
    FinancialNotification, ApprovalWorkflow, FinancialDashboard, FeeAutomationRule,
    BillItem, StudentBill, StudentBillItem, ClassBill, Payment, StudentCredit,
    GradingSystem, AssessmentType, Assessment, ResultModeSetting, Result,
    ReportResults, ReportResultDetail, ReportRemark, TermResult, AnnualResult,
    Student, StudentRegistrationCSV, ClassRegister,
    Subject,
    Class, Stream, Term, AcademicClass, AcademicClassStream, ClassSubjectAllocation,
    StaffAccount
)
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Populate all models with sample data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake = Faker()

    def handle(self, *args, **options):
        self.stdout.write('Starting data population...')

        # Populate basic settings
        self.populate_currency()
        self.populate_academic_year()
        self.populate_section()
        self.populate_signature()
        self.populate_department()

        # Populate roles and staff
        self.populate_roles()
        self.populate_staff()
        self.populate_bank_details()
        self.populate_staff_documents()
        self.populate_staff_accounts()

        # Populate classes and subjects
        self.populate_subjects()
        self.populate_classes()
        self.populate_terms()
        self.populate_academic_classes()
        self.populate_academic_class_streams()
        self.populate_class_subject_allocations()

        # Populate students
        self.populate_students()
        self.populate_class_registers()

        # Populate timetables
        self.populate_classrooms()
        self.populate_time_slots()
        self.populate_break_periods()
        self.populate_timetables()

        # Populate finance
        self.populate_bank_accounts()
        self.populate_vendors()
        self.populate_expenses()
        self.populate_budgets()
        self.populate_budget_items()
        self.populate_expenditures()
        self.populate_expenditure_items()
        self.populate_income_sources()
        self.populate_transactions()
        self.populate_bank_statements()
        self.populate_bank_transactions()
        self.populate_cash_flow_statements()
        self.populate_financial_notifications()
        self.populate_approval_workflows()
        self.populate_financial_dashboards()
        self.populate_fee_automation_rules()

        # Populate fees and payments
        self.populate_bill_items()
        self.populate_student_bills()
        self.populate_student_bill_items()
        self.populate_class_bills()
        self.populate_payments()
        self.populate_student_credits()

        # Populate results
        self.populate_grading_systems()
        self.populate_assessment_types()
        self.populate_assessments()
        self.populate_results()
        self.populate_report_results()
        self.populate_report_result_details()
        self.populate_report_remarks()
        self.populate_term_results()
        self.populate_annual_results()

        self.stdout.write(self.style.SUCCESS('Data population completed!'))

    def populate_currency(self):
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'SEK', 'NZD']
        for currency in currencies:
            Currency.objects.create(
                code=currency,
                desc=self.fake.currency_name(),
                cost=self.fake.random_number(digits=2)
            )

    def populate_academic_year(self):
        for i in range(10):
            AcademicYear.objects.create(
                academic_year=f"202{i}-202{i+1}",
                is_current=(i == 9)  # Only the last one is current
            )

    def populate_section(self):
        for _ in range(10):
            Section.objects.create(
                section_name=self.fake.word()
            )

    def populate_signature(self):
        for _ in range(10):
            Signature.objects.create(
                position=random.choice(['Headteacher', 'Deputy Headteacher', 'Bursar', 'Clerk']),
                signature=self.fake.image_url()
            )

    def populate_department(self):
        for _ in range(10):
            Department.objects.create(
                name=random.choice(['Academic', 'Administrative', 'Support'])
            )

    def populate_roles(self):
        roles = ['Teacher', 'Principal', 'Clerk', 'Librarian', 'Counselor', 'Nurse', 'Security', 'Driver', 'Cook', 'Janitor']
        for role in roles:
            Role.objects.create(name=role)

    def populate_staff(self):
        for _ in range(10):
            Staff.objects.create(
                first_name=self.fake.first_name(),
                last_name=self.fake.last_name(),
                birth_date=self.fake.date_of_birth(),
                gender=random.choice(['M', 'F']),
                address=self.fake.address(),
                marital_status=random.choice(['Single', 'Married', 'Divorced']),
                contacts=self.fake.phone_number(),
                email=self.fake.email(),
                qualification=self.fake.job(),
                hire_date=self.fake.date_this_decade(),
                department=random.choice(['Academic', 'Administrative', 'Support']),
                salary=random.uniform(1000, 5000),
                is_academic_staff=random.choice([True, False]),
                is_administrator_staff=random.choice([True, False]),
                is_support_staff=random.choice([True, False]),
                staff_status=random.choice(['Active', 'Inactive'])
            )

    def populate_bank_details(self):
        for staff in Staff.objects.all():
            BankDetail.objects.create(
                staff=staff,
                bank_name=self.fake.company(),
                branch_name=self.fake.city(),
                account_no=self.fake.iban(),
                account_name=self.fake.name()
            )

    def populate_staff_documents(self):
        for staff in Staff.objects.all():
            StaffDocument.objects.create(
                staff=staff,
                document_type=random.choice(['ID', 'Certificate', 'Contract']),
                file=self.fake.file_path()
            )

    def populate_staff_accounts(self):
        for staff in Staff.objects.all():
            role = Role.objects.order_by('?').first()
            user = User.objects.create_user(
                username=self.fake.user_name(),
                email=staff.email,
                password='password123'
            )
            StaffAccount.objects.create(
                staff=staff,
                user=user,
                role=role
            )

    def populate_subjects(self):
        subjects = ['Mathematics', 'English', 'Science', 'History', 'Geography', 'Art', 'Music', 'Physical Education', 'Computer Science', 'Biology']
        for subject in subjects:
            Subject.objects.create(
                code=self.fake.word().upper(),
                name=subject,
                description=self.fake.text(),
                credit_hours=random.randint(1, 5),
                section=Section.objects.order_by('?').first(),
                type=random.choice(['Core', 'Elective'])
            )

    def populate_classes(self):
        classes = ['Baby Class', 'Middle Class', 'Top Class', 'Primary 1', 'Primary 2', 'Primary 3', 'Primary 4', 'Primary 5', 'Primary 6', 'Primary 7', 'Secondary 1', 'Secondary 2', 'Secondary 3', 'Secondary 4', 'Senior 1', 'Senior 2', 'Senior 3', 'Senior 4', 'Senior 5', 'Senior 6']
        for cls in classes:
            Class.objects.create(
                name=cls,
                code=self.fake.word().upper(),
                section=Section.objects.order_by('?').first()
            )

    def populate_terms(self):
        terms = ['Term 1', 'Term 2', 'Term 3']
        for term in terms:
            academic_year = AcademicYear.objects.order_by('?').first()
            Term.objects.create(
                term=term,
                academic_year=academic_year,
                start_date=self.fake.date_this_year(),
                end_date=self.fake.date_this_year(),
                is_current=random.choice([True, False])
            )

    def populate_academic_classes(self):
        terms = list(Term.objects.all())
        for i, cls in enumerate(Class.objects.all()):
            for j, academic_year in enumerate(AcademicYear.objects.all()):
                term = terms[(i + j) % len(terms)]
                AcademicClass.objects.get_or_create(
                    Class=cls,
                    academic_year=academic_year,
                    term=term,
                    defaults={'section': Section.objects.order_by('?').first(), 'fees_amount': random.uniform(1000, 5000)}
                )

    def populate_academic_class_streams(self):
        streams = ['A', 'B', 'C', 'D', 'E']
        for stream in streams:
            Stream.objects.create(
                stream=stream
            )
        for academic_class in AcademicClass.objects.all():
            stream = Stream.objects.order_by('?').first()
            AcademicClassStream.objects.create(
                academic_class=academic_class,
                stream=stream,
                class_teacher=Staff.objects.filter(is_academic_staff=True).order_by('?').first()
            )

    def populate_class_subject_allocations(self):
        for academic_class_stream in AcademicClassStream.objects.all():
            subject = Subject.objects.order_by('?').first()
            staff = Staff.objects.filter(is_academic_staff=True).order_by('?').first()
            ClassSubjectAllocation.objects.create(
                academic_class_stream=academic_class_stream,
                subject=subject,
                subject_teacher=staff
            )

    def populate_students(self):
        for _ in range(50):
            academic_year = AcademicYear.objects.order_by('?').first()
            Student.objects.create(
                reg_no=self.fake.unique.random_number(digits=8),
                student_name=self.fake.name(),
                gender=random.choice(['M', 'F']),
                birthdate=self.fake.date_of_birth(),
                nationality=random.choice(['Ugandan', 'Kenyan', 'Tanzanian', 'Rwandan', 'Burundian', 'South Sudanese']),
                religion=random.choice(['Christian', 'Muslim', 'Hindu', 'Traditional']),
                address=self.fake.address(),
                guardian=self.fake.name(),
                relationship=random.choice(['Father', 'Mother', 'Guardian']),
                contact=self.fake.phone_number(),
                academic_year=academic_year,
                current_class=Class.objects.order_by('?').first(),
                stream=Stream.objects.order_by('?').first(),
                term=Term.objects.order_by('?').first()
            )

    def populate_class_registers(self):
        for student in Student.objects.all():
            academic_class_stream = AcademicClassStream.objects.order_by('?').first()
            ClassRegister.objects.create(
                academic_class_stream=academic_class_stream,
                student=student,
                payment_status=random.choice(['0', '1', '2'])
            )

    def populate_classrooms(self):
        for _ in range(10):
            Classroom.objects.create(
                name=f"Room {random.randint(1, 100)}",
                capacity=random.randint(20, 50),
                location=self.fake.address()
            )

    def populate_time_slots(self):
        for i in range(10):
            TimeSlot.objects.create(
                start_time=self.fake.time(),
                end_time=self.fake.time()
            )

    def populate_break_periods(self):
        existing_combinations = set(BreakPeriod.objects.values_list('weekday', 'time_slot'))
        for _ in range(10):
            time_slot = TimeSlot.objects.order_by('?').first()
            weekday = random.choice(['MON', 'TUE', 'WED', 'THU', 'FRI'])
            if (weekday, time_slot.id) not in existing_combinations:
                BreakPeriod.objects.create(
                    weekday=weekday,
                    name=self.fake.word(),
                    time_slot=time_slot
                )
                existing_combinations.add((weekday, time_slot.id))

    def populate_timetables(self):
        for academic_class_stream in AcademicClassStream.objects.all():
            time_slot = TimeSlot.objects.order_by('?').first()
            subject = Subject.objects.order_by('?').first()
            weekday = random.choice(['MON', 'TUE', 'WED', 'THU', 'FRI'])
            # Find a teacher not already assigned at this time
            teacher = None
            for t in Staff.objects.filter(is_academic_staff=True).order_by('?'):
                if not Timetable.objects.filter(teacher=t, weekday=weekday, time_slot=time_slot).exists():
                    teacher = t
                    break
            # Find a classroom not already in use at this time
            classroom = None
            for c in Classroom.objects.order_by('?'):
                if not Timetable.objects.filter(classroom=c, weekday=weekday, time_slot=time_slot).exists():
                    classroom = c
                    break
            if teacher and classroom:
                Timetable.objects.create(
                    class_stream=academic_class_stream,
                    weekday=weekday,
                    time_slot=time_slot,
                    subject=subject,
                    teacher=teacher,
                    classroom=classroom
                )

    def populate_bank_accounts(self):
        for _ in range(10):
            BankAccount.objects.create(
                bank_name=self.fake.company(),
                account_number=self.fake.iban(),
                account_name=self.fake.name(),
                account_type=random.choice(['Savings', 'Checking', 'Business']),
                balance=random.uniform(1000, 100000)
            )

    def populate_vendors(self):
        for _ in range(10):
            Vendor.objects.create(
                name=self.fake.company(),
                contact=self.fake.phone_number(),
                email=self.fake.email(),
                address=self.fake.address()
            )

    def populate_expenses(self):
        for _ in range(10):
            Expense.objects.create(
                name=self.fake.word(),
                description=self.fake.text()
            )

    def populate_budgets(self):
        for academic_year in AcademicYear.objects.all():
            term = Term.objects.order_by('?').first()
            Budget.objects.create(
                academic_year=academic_year,
                term=term,
                status=random.choice(['Open', 'Closed'])
            )

    def populate_budget_items(self):
        for budget in Budget.objects.all():
            department = Department.objects.order_by('?').first()
            expense = Expense.objects.order_by('?').first()
            BudgetItem.objects.create(
                budget=budget,
                department=department,
                expense=expense,
                allocated_amount=random.uniform(1000, 10000)
            )

    def populate_expenditures(self):
        for budget_item in BudgetItem.objects.all():
            vendor = Vendor.objects.order_by('?').first()
            Expenditure.objects.create(
                budget_item=budget_item,
                vendor=vendor,
                description=self.fake.text(),
                vat=random.uniform(10, 100),
                date_incurred=self.fake.date_this_year(),
                approved_by=Staff.objects.order_by('?').first(),
                payment_status=random.choice(['Pending', 'Approved', 'Paid'])
            )

    def populate_expenditure_items(self):
        for expenditure in Expenditure.objects.all():
            ExpenditureItem.objects.create(
                expenditure=expenditure,
                item_name=self.fake.word(),
                quantity=random.randint(1, 10),
                units=random.choice(['pieces', 'kg', 'liters']),
                unit_cost=random.uniform(10, 100)
            )

    def populate_income_sources(self):
        for _ in range(10):
            IncomeSource.objects.create(
                name=self.fake.word(),
                description=self.fake.text()
            )

    def populate_transactions(self):
        for _ in range(10):
            Transaction.objects.create(
                date=self.fake.date_this_year(),
                amount=random.uniform(100, 10000),
                type=random.choice(['INCOME', 'EXPENSE']),
                description=self.fake.text(),
                bank_account=BankAccount.objects.order_by('?').first(),
                income_source=IncomeSource.objects.order_by('?').first() if random.choice([True, False]) else None,
                expense=Expense.objects.order_by('?').first() if random.choice([True, False]) else None
            )

    def populate_bank_statements(self):
        for bank_account in BankAccount.objects.all():
            BankStatement.objects.create(
                bank_account=bank_account,
                statement_date=self.fake.date_this_year(),
                opening_balance=random.uniform(1000, 10000),
                closing_balance=random.uniform(1000, 10000)
            )

    def populate_bank_transactions(self):
        for bank_statement in BankStatement.objects.all():
            BankTransaction.objects.create(
                bank_statement=bank_statement,
                date=self.fake.date_this_year(),
                description=self.fake.text(),
                amount=random.uniform(100, 1000),
                type=random.choice(['DEBIT', 'CREDIT'])
            )

    def populate_cash_flow_statements(self):
        for _ in range(10):
            CashFlowStatement.objects.create(
                start_date=self.fake.date_this_year(),
                end_date=self.fake.date_this_year(),
                operating_activities=random.uniform(1000, 10000),
                investing_activities=random.uniform(-5000, 5000),
                financing_activities=random.uniform(-5000, 5000),
                net_cash_flow=random.uniform(-10000, 10000)
            )

    def populate_financial_notifications(self):
        for _ in range(10):
            FinancialNotification.objects.create(
                title=self.fake.sentence(),
                message=self.fake.text(),
                type=random.choice(['BUDGET_ALERT', 'PAYMENT_REMINDER', 'EXPENSE_APPROVAL']),
                recipient=Staff.objects.order_by('?').first(),
                is_read=random.choice([True, False])
            )

    def populate_approval_workflows(self):
        for expenditure in Expenditure.objects.all():
            ApprovalWorkflow.objects.create(
                expenditure=expenditure,
                approver=Staff.objects.order_by('?').first(),
                status=random.choice(['PENDING', 'APPROVED', 'REJECTED']),
                comments=self.fake.text(),
                approval_date=self.fake.date_this_year() if random.choice([True, False]) else None
            )

    def populate_financial_dashboards(self):
        for _ in range(10):
            FinancialDashboard.objects.create(
                title=self.fake.sentence(),
                chart_type=random.choice(['BAR', 'LINE', 'PIE']),
                data_source=self.fake.url(),
                created_by=Staff.objects.order_by('?').first()
            )

    def populate_fee_automation_rules(self):
        for _ in range(10):
            FeeAutomationRule.objects.create(
                name=self.fake.word(),
                rule_type=random.choice(['DISCOUNT', 'PENALTY', 'WAIVER']),
                condition=self.fake.text(),
                action=self.fake.text(),
                is_active=random.choice([True, False])
            )

    def populate_bill_items(self):
        for _ in range(10):
            BillItem.objects.create(
                name=self.fake.word(),
                amount=random.uniform(10, 100),
                bill_duration=random.choice(['TERM', 'YEAR', 'MONTH']),
                category=random.choice(['TUITION', 'EXAM', 'TRANSPORT', 'MEALS']),
                description=self.fake.text(),
                is_active=random.choice([True, False])
            )

    def populate_student_bills(self):
        for student in Student.objects.all():
            academic_year = AcademicYear.objects.order_by('?').first()
            term = Term.objects.order_by('?').first()
            StudentBill.objects.create(
                student=student,
                academic_year=academic_year,
                term=term,
                total_amount=random.uniform(100, 1000),
                paid_amount=random.uniform(0, 500),
                balance=random.uniform(0, 500),
                due_date=self.fake.date_this_year(),
                status=random.choice(['UNPAID', 'PARTIAL', 'PAID'])
            )

    def populate_student_bill_items(self):
        for student_bill in StudentBill.objects.all():
            bill_item = BillItem.objects.order_by('?').first()
            StudentBillItem.objects.create(
                bill=student_bill,
                bill_item=bill_item,
                amount=random.uniform(10, 100),
                quantity=random.randint(1, 5)
            )

    def populate_class_bills(self):
        for academic_class in AcademicClass.objects.all():
            academic_year = AcademicYear.objects.order_by('?').first()
            term = Term.objects.order_by('?').first()
            ClassBill.objects.create(
                academic_class=academic_class,
                academic_year=academic_year,
                term=term,
                total_amount=random.uniform(1000, 10000),
                description=self.fake.text()
            )

    def populate_payments(self):
        for student_bill in StudentBill.objects.all():
            Payment.objects.create(
                bill=student_bill,
                amount=random.uniform(10, 500),
                payment_date=self.fake.date_this_year(),
                payment_method=random.choice(['CASH', 'BANK', 'MOBILE']),
                reference_number=self.fake.uuid4(),
                received_by=Staff.objects.order_by('?').first()
            )

    def populate_student_credits(self):
        for student in Student.objects.all():
            StudentCredit.objects.create(
                student=student,
                amount=random.uniform(10, 100),
                reason=self.fake.text(),
                date_granted=self.fake.date_this_year(),
                granted_by=Staff.objects.order_by('?').first()
            )

    def populate_grading_systems(self):
        for _ in range(10):
            GradingSystem.objects.create(
                grade=self.fake.random_letter().upper(),
                min_score=random.uniform(0, 100),
                max_score=random.uniform(0, 100),
                remarks=self.fake.text()
            )

    def populate_assessment_types(self):
        assessment_types = ['Quiz', 'Test', 'Exam', 'Assignment', 'Project', 'Presentation', 'Lab', 'Homework', 'Midterm', 'Final']
        for atype in assessment_types:
            AssessmentType.objects.create(
                name=atype,
                description=self.fake.text(),
                weight=random.uniform(0.1, 1.0)
            )

    def populate_assessments(self):
        for academic_class in AcademicClass.objects.all():
            assessment_type = AssessmentType.objects.order_by('?').first()
            subject_allocation = ClassSubjectAllocation.objects.order_by('?').first()
            term = Term.objects.order_by('?').first()
            Assessment.objects.create(
                academic_class=academic_class,
                assessment_type=assessment_type,
                subject_allocation=subject_allocation,
                term=term,
                name=self.fake.sentence(),
                date=self.fake.date_this_year(),
                total_marks=random.uniform(10, 100),
                passing_marks=random.uniform(5, 50)
            )

    def populate_results(self):
        for assessment in Assessment.objects.all():
            for student in Student.objects.all()[:5]:  # Limit to 5 students per assessment
                Result.objects.create(
                    assessment=assessment,
                    student=student,
                    marks_obtained=random.uniform(0, assessment.total_marks),
                    grade=GradingSystem.objects.order_by('?').first(),
                    remarks=self.fake.text()
                )

    def populate_report_results(self):
        for student in Student.objects.all():
            academic_year = AcademicYear.objects.order_by('?').first()
            term = Term.objects.order_by('?').first()
            ReportResults.objects.create(
                student=student,
                academic_year=academic_year,
                term=term,
                total_marks=random.uniform(0, 1000),
                average_marks=random.uniform(0, 100),
                position=random.randint(1, 50)
            )

    def populate_report_result_details(self):
        for report in ReportResults.objects.all():
            subject = Subject.objects.order_by('?').first()
            ReportResultDetail.objects.create(
                report=report,
                subject=subject,
                marks=random.uniform(0, 100),
                grade=GradingSystem.objects.order_by('?').first()
            )

    def populate_report_remarks(self):
        for student in Student.objects.all():
            ReportRemark.objects.create(
                student=student,
                academic_year=AcademicYear.objects.order_by('?').first(),
                term=Term.objects.order_by('?').first(),
                remarks=self.fake.text(),
                teacher=Staff.objects.filter(is_academic_staff=True).order_by('?').first()
            )

    def populate_term_results(self):
        for student in Student.objects.all():
            academic_year = AcademicYear.objects.order_by('?').first()
            term = Term.objects.order_by('?').first()
            TermResult.objects.create(
                student=student,
                academic_year=academic_year,
                term=term,
                total_marks=random.uniform(0, 1000),
                average_marks=random.uniform(0, 100),
                position=random.randint(1, 50),
                promoted=random.choice([True, False])
            )

    def populate_annual_results(self):
        for student in Student.objects.all():
            academic_year = AcademicYear.objects.order_by('?').first()
            AnnualResult.objects.create(
                student=student,
                academic_year=academic_year,
                total_marks=random.uniform(0, 1200),
                average_marks=random.uniform(0, 100),
                position=random.randint(1, 50),
                overall_grade=GradingSystem.objects.order_by('?').first()
            )
