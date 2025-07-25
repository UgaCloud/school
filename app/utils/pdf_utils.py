from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_student_report_pdf(student, assessments):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x = 50
    y = height - 50

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(x, y, f"Performance Report for {student.student_name}")
    y -= 30

    # Student Info
    p.setFont("Helvetica", 12)
    p.drawString(x, y, f"Reg No: {student.reg_no}")
    y -= 20
    p.drawString(x, y, f"Gender: {student.gender}")
    y -= 20
    p.drawString(x, y, f"Nationality: {student.nationality}")
    y -= 30

    # Table Headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x, y, "Subject")
    p.drawString(x + 180, y, "Assessment")
    p.drawString(x + 330, y, "Score")
    p.drawString(x + 400, y, "Grade")
    y -= 20
    p.line(x, y, x + 500, y)
    y -= 10

    # Table Rows
    p.setFont("Helvetica", 12)
    for result in assessments:
        if y < 80:  # Start new page
            p.showPage()
            y = height - 50

        p.drawString(x, y, result.assessment.subject.name)
        p.drawString(x + 180, y, result.assessment.assessment_type.name)
        p.drawString(x + 330, y, str(result.score))
        p.drawString(x + 400, y, result.grade)
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
