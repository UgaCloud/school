from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.utils import timezone

def generate_student_report_pdf(student, assessments):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x = 50
    y = height - 50

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(x, y, f"Exam Report for {student.student_name}")
    y -= 30

    # Student Info
    p.setFont("Helvetica", 12)
    p.drawString(x, y, f"Reg No: {student.reg_no}")
    y -= 20
    p.drawString(x, y, f"Class: {student.current_class.name if student.current_class else 'N/A'}")
    y -= 20
    p.drawString(x, y, f"Date Generated: {timezone.now().strftime('%Y-%m-%d')}")
    y -= 30

    # Table Headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x, y, "S.No")
    p.drawString(x + 50, y, "Subject")
    p.drawString(x + 200, y, "Assessment Type")
    p.drawString(x + 350, y, "Date")
    p.drawString(x + 450, y, "Score")
    p.drawString(x + 520, y, "Grade")
    y -= 20
    p.line(x, y, x + 570, y)
    y -= 10

    # Table Rows
    p.setFont("Helvetica", 10)
    for index, result in enumerate(assessments, start=1):
        if y < 80:  # Start new page
            p.showPage()
            x = 50
            y = height - 50
            # Redraw headers on new page
            p.setFont("Helvetica-Bold", 12)
            p.drawString(x, y, "S.No")
            p.drawString(x + 50, y, "Subject")
            p.drawString(x + 200, y, "Assessment Type")
            p.drawString(x + 350, y, "Date")
            p.drawString(x + 450, y, "Score")
            p.drawString(x + 520, y, "Grade")
            y -= 20
            p.line(x, y, x + 570, y)
            y -= 10
            p.setFont("Helvetica", 10)

        p.drawString(x, y, str(index))
        p.drawString(x + 50, y, result.assessment.subject.name)
        p.drawString(x + 200, y, result.assessment.assessment_type.name)
        p.drawString(x + 350, y, result.assessment.date.strftime('%Y-%m-%d'))
        p.drawString(x + 450, y, str(result.score))
        p.drawString(x + 520, y, result.grade)
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
