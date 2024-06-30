import csv

from app.selectors.school_settings import get_current_academic_year
from app.selectors.classes import get_academic_class, get_academic_class_stream, get_class_by_code, get_stream_by_name
from app.models.students import ClassRegister, StudentRegistrationCSV
from app.models.students import Student

def register_student(student, _class, term, stream):
    current_academic_year = get_current_academic_year()
    academic_class = get_academic_class(current_academic_year, _class,term)
    class_stream = get_academic_class_stream(academic_class, stream)
    
    class_register = ClassRegister(_class=class_stream, student=student)
    class_register.save()
    
    return class_register
    
def bulk_student_registration(csv_obj):
    with open(csv_obj.file_name.path, 'r') as f:
        reader = csv.reader(f)
       
        for i, row in enumerate(reader):
            if i >= 2:  # Ignore first 2 rows
                reg_no = row[0]
                student_name = row[1]
                gender = row[2]
                birthdate = row[3]
                nationality = row[4]
                religion = row[5]
                address = row[6]
                guardian = row[7]
                relationship = row[8]
                contact = row[9]
                year = row[10]
                class_code = row[11]
                stream_name = row[12]
                term = row[13]

                academic_year = get_current_academic_year()
                current_class = get_class_by_code(class_code)
                stream = get_stream_by_name(stream_name)
                
                student = Student(reg_no=reg_no, 
                    student_name = student_name, gender=gender,
                    birthdate = birthdate, nationality = nationality,religion = religion, address = address,
                    guardian = guardian, relationship = relationship,
                    contact = contact, academic_year = academic_year,
                    current_class = current_class, stream = stream,
                    term = term
                    )
                student.save()
                
                register_student(student, student.current_class, student.term, student.stream)
                
def delete_all_csv_files():
    StudentRegistrationCSV.objects.all().delete()
        

   
    
    