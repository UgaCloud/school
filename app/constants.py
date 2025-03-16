# Roles


STUDENT = "Student"
TEACHER = "Teacher"
CLASS_TEACHER = "Class Teacher"
BURSAR = "Bursar"
DOS = "DOS"
HEADTEACHER = "Headteacher"
######## End of Roles ############

POSITION_SIGNATURE_CHOICES=[
    ("HEAD TEACHER", "HEAD TEACHER"),
    ("DIRECTOR OF STUDIES", "DIRECTOR OF STUDIES"),
    ("CLASS TEACHER", "CLASS TEACHER"),

]

##### Authentication Roles ###########
ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Teacher', 'Teacher'),
        ('Bursar', 'Bursar'),
        ('Director of Studies', 'Director of Studies'),
        ('Head master', 'Head master'),
        ('Class Teacher', 'Class Teacher'),
 ]

# Types
ACADEMIC = 'Academic'
FINANCE = 'Finance'
ADMINISTRATION = 'Administration'
SECURITY = 'Security'
TRANSPORT = 'Transport'
SUPPORT = 'Support'

TYPE_CHOICES = [
    (STUDENT, STUDENT),
    (ACADEMIC, ACADEMIC),
    (FINANCE, FINANCE),
    (ADMINISTRATION, ADMINISTRATION),
    (SECURITY, SECURITY),
    (TRANSPORT, TRANSPORT),
    (SUPPORT, SUPPORT)
]
TERMS = [
    ("1", "I"),
    ("2", "II"),
    ("3", "III"),
]
GENDERS = [
    ("M", "Male"),
    ("F", "Female")
]

MARITAL_STATUS = [
    ("M", "Married"),
    ("U", "Unmarried")
]

EMPLOYEE_STATUS = [
        ('Active', 'Active'),
        ('On Leave', 'On Leave'),
        ('Retired', 'Retired')
    ]

RELIGIONS = [
    ("Muslim", "Muslim"),
    ("Protestant", "Protestant"),
    ("Catholic", "Catholic"),
    ("Adventist", "Adventist"),
    ("Others", "Others"),
]

NATIONALITIES = [
    ("Ugandan", "Ugandan"),
    ("Kenyan", "Kenyan"),
    ("Tanzanian", "Tanzanian"),
    ("Rwanda", "Rwanda"),
    ("South Sudan", "South Sudan"),
    ("Burundi", "Burundi"),
    ("Somali","Somali")
]

BILL_STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Overdue', 'Overdue')
    ]

BILL_CATEGORY_CHOICES = [
        ('One Off', 'One Off'),
        ('Recurring', 'Recurring'),
    ]

BILL_DURATION_CHOICES = [
        ('None', 'None'),
        ('Termly', 'Termly'),
        ('Annually', 'Annually'),
    ]

PAYMENT_METHODS = [
    ('Cash', 'Cash'),
    ('School Pay', 'School Pay'),
    ('Bank', 'Bank')
]

PAYMENT_STATUS = [
    ('Pending', 'Pending'), 
    ('Paid', 'Paid')
]

SUCCESS_ADD_MESSAGE = "Record Saved!"

SUCCESS_EDIT_MESSAGE = "Changes Saved"
SUCCESS_BULK_ADD_MESSAGE = "All Record Saved!"

CONFIRMATION_MESSAGE ="Are you sure you want to delete this field?"
DELETE_MESSAGE = "Record Deleted"
FAILURE_LOGIN_MESSAGE="Invalid username or password"
FAILURE_MESSAGE = "Something Went Wrong!, Check your inputs and Try again"

INTEGRITY_ERROR_MESSAGE = "The record you tried to add is a duplicate or contains duplicate values" \
                          " for unique fields."

INVALID_VALUE_MESSAGE = "One or more values provided is/are invalid or duplicate for unique fields."

MEASUREMENTS = [
    ("Piece", "Piece"),
    ("Set", "Set"),
    ("Pair", "Pair"),
    ("Box", "Box"),
    ("Kgs", "Kgs"),
    ("Litre", "Litre"),
    ("Jerry Can", "Jerry Can"),
]

WAGE_BILL_PAYMENT_GENERATION_CONFIRM_MESSAGE \
    = "This operation can only be done once. All payables on unapproved " \
      "submitted wage sheets will not be included in the wage bill payments " \
      "for Wage bill week"

PALETTE = ['#465b65', '#184c9c', '#d33035', '#ffc107', '#28a745', '#6f7f8c', '#6610f2', '#6e9fa5', '#fd7e14',
           '#e83e8c', '#17a2b8', '#6f42c1']
