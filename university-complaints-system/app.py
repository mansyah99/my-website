from flask import Flask, render_template, request, redirect, url_for ,session , send_from_directory
from db_connection import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import os #حتى نتعامل مع الملفات في حالة رفع ملفات في المستقبل
from werkzeug.utils import secure_filename # حتى نستخدمها في حالة رفع ملفات في المستقبل عشان نضمن ان اسم الملف آمن وما يحتوي على أحرف خاصة أو مسارات غير مرغوب فيها.
from difflib import SequenceMatcher # حتى نستخدمها في حالة البحث عن شكاوى معينة في صفحة شكاوى القسم، هذا بيخلينا نقدر نعمل بحث تقريبي عن طريق مقارنة نص البحث مع عناوين الشكاوى واختيار الشكاوى اللي فيها تشابه عالي مع نص البحث.
import re # حتى نستخدمها في حالة البحث عن شكاوى معينة في صفحة شكاوى القسم، هذا بيخلينا نقدر نستخدم التعبيرات النمطية (regular expressions) لتحليل نص البحث وتحديد إذا كان المستخدم يبحث عن رقم شكوى معين أو عن نص في عنوان الشكوى.
from datetime import datetime # حتى نستخدمها في حالة عرض تفاصيل الشكوى، هذا بيخلينا نقدر نعرض تاريخ تقديم الشكوى بشكل منسق وجميل في صفحة تفاصيل الشكوى.


app = Flask(__name__)
app.secret_key = "my_secret_key_123" # هون بنحدد مفتاح سري للجلسة (secret key) في تطبيق Flask، هذا المفتاح يستخدم لتوقيع بيانات الجلسة وضمان سلامتها، يعني لما نستخدم session في Flask لتخزين بيانات المستخدم مثل user_id و full_name و role و department_id، Flask بيستخدم هذا المفتاح السري لتوقيع هذه البيانات، وهذا بيمنع أي شخص من تعديل بيانات الجلسة أو تزويرها، لأنه بدون معرفة هذا المفتاح السري، ما راح يقدر أحد يغير بيانات الجلسة بشكل غير مصرح به. لذلك من المهم اختيار مفتاح سري قوي وفريد لتأمين جلسات المستخدمين في التطبيق.
app.config['UPLOAD_FOLDER'] = 'uploads'
def normalize_text(text): # هون بنعرف دالة normalize_text اللي بتستخدم لتنظيف النصوص قبل ما نستخدمها في عمليات البحث أو المقارنة، هذا بيخلينا نقدر نتعامل مع النصوص بشكل أكثر مرونة ونتجنب مشاكل مثل اختلاف الحروف الكبيرة والصغيرة أو وجود مسافات زائدة.
    text = text or ""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text

def calculate_similarity(text1, text2):
    return SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()

        conn.close()

        if user:
            if user.is_active == 0:
                message = "هذا الحساب غير مفعل، يرجى مراجعة الإدارة"
            else:
                db_password = user.password
                role = user.role

                if check_password_hash(db_password, password):
                    session["user_id"] = user.user_id
                    session["full_name"] = user.full_name
                    session["role"] = user.role
                    session["department_id"] = user.department_id
                    session["unit_id"] = user.unit_id

                    if role == "admin":
                        return redirect(url_for("admin_dashboard"))
                    elif role == "employee":
                        return redirect(url_for("employee_dashboard"))
                    elif role == "student":
                        return redirect(url_for("student_dashboard"))
                else:
                    message = "كلمة المرور غير صحيحة"
        else:
            message = "البريد الإلكتروني غير موجود"

    return render_template("login.html", message=message)

@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        university_number = request.form["university_number"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            message = "هذا البريد الإلكتروني مستخدم مسبقًا"
        else:
            hashed_password = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO Users (full_name, email, password, role, university_number, department_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (full_name, email, hashed_password, "student", university_number, None, 1))
            conn.commit()
            message = "تم إنشاء الحساب بنجاح"

        conn.close()

    return render_template("register.html", message=message)

@app.route("/student")  
def student_dashboard():
    if session.get("role") != "student": # هون بنتحقق من دور المستخدم في الجلسة، إذا ما كان دوره "student" بنعيد توجيهه إلى الصفحة الرئيسية (home) عشان ما يقدر يوصل إلى لوحة تحكم الطالب.
        return redirect(url_for("login"))
    full_name = session.get("full_name") # هون بنجيب اسم المستخدم من الجلسة، وإذا ما كان موجود بنعرض كلمة "طالب" كاسم افتراضي
    return render_template("student_dashboard.html", full_name=full_name) # هون بنمرر اسم المستخدم إلى صفحة لوحة تحكم الطالب عشان نقدر نعرضه في الصفحة ونرحب بالطالب باسمه.

@app.route("/employee")
def employee_dashboard():
    if session.get("role") != "employee":
        return redirect(url_for("login"))

    department_id = session.get("department_id")
    full_name = session.get("full_name")

    conn = get_db_connection()
    cursor = conn.cursor()

    # عدد كل شكاوى القسم الأساسي
    cursor.execute("""
        SELECT COUNT(*)
        FROM Complaints
        WHERE department_id = ? AND status != 'Cancelled'
    """, (department_id,))
    total_complaints = cursor.fetchone()[0]

    # بانتظار المعالجة
    cursor.execute("""
        SELECT COUNT(*)
        FROM Complaints
        WHERE department_id = ? AND status = 'Pending'
    """, (department_id,))
    pending_count = cursor.fetchone()[0]

    # قيد المعالجة
    cursor.execute("""
        SELECT COUNT(*)
        FROM Complaints
        WHERE department_id = ? AND status = 'In Progress'
    """, (department_id,))
    in_progress_count = cursor.fetchone()[0]

    # المحلولة
    cursor.execute("""
        SELECT COUNT(*)
        FROM Complaints
        WHERE department_id = ? AND status = 'Resolved'
    """, (department_id,))
    resolved_count = cursor.fetchone()[0]
   
    cursor.execute("""
    SELECT COUNT(*)
    FROM Complaints
    JOIN Departments ON Complaints.department_id = Departments.department_id
    WHERE Complaints.department_id = ?
      AND Complaints.status IN ('Pending', 'In Progress')
      AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) > Departments.sla_days
""", (department_id,))
    overdue_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM Complaints
    WHERE department_id = ?
      AND status = 'Cancelled'
""", (department_id,))
    cancelled_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
    "employee_dashboard.html",
    full_name=session.get("full_name"),
    total_complaints=total_complaints,
    pending_count=pending_count,
    in_progress_count=in_progress_count,
    resolved_count=resolved_count,
    overdue_count=overdue_count,
    cancelled_count=cancelled_count
)

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    full_name = session.get("full_name")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_employees FROM Users WHERE role = 'employee'")
    total_employees = cursor.fetchone().total_employees

    cursor.execute("SELECT COUNT(*) AS total_students FROM Users WHERE role = 'student'")
    total_students = cursor.fetchone().total_students

    cursor.execute("SELECT COUNT(*) AS total_complaints FROM Complaints")
    total_complaints = cursor.fetchone().total_complaints

    cursor.execute("SELECT COUNT(*) AS pending_complaints FROM Complaints WHERE status = 'Pending'")
    pending_complaints = cursor.fetchone().pending_complaints

    cursor.execute("SELECT COUNT(*) AS in_progress_complaints FROM Complaints WHERE status = 'In Progress'")
    in_progress_complaints = cursor.fetchone().in_progress_complaints

    cursor.execute("SELECT COUNT(*) AS resolved_complaints FROM Complaints WHERE status = 'Resolved'")
    resolved_complaints = cursor.fetchone().resolved_complaints

    cursor.execute("SELECT COUNT(*) AS cancelled_complaints FROM Complaints WHERE status = 'Cancelled'")
    cancelled_complaints = cursor.fetchone().cancelled_complaints

    # متوسط التقييم العام
    cursor.execute("""
        SELECT AVG(CAST(rating AS FLOAT)) AS average_rating
        FROM Complaint_Feedback
    """)
    avg_rating_row = cursor.fetchone()
    average_rating = round(avg_rating_row.average_rating, 1) if avg_rating_row and avg_rating_row.average_rating is not None else 0

    # عدد الشكاوى التي تم تقييمها
    cursor.execute("""
        SELECT COUNT(*) AS rated_complaints_count
        FROM Complaint_Feedback
    """)
    rated_complaints_count = cursor.fetchone().rated_complaints_count

    # الشكاوى المتأخرة حاليًا
    cursor.execute("""
        SELECT COUNT(*) AS overdue_complaints_count
        FROM Complaints
        JOIN Departments ON Complaints.department_id = Departments.department_id
        WHERE Complaints.status IN ('Pending', 'In Progress')
          AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) > Departments.sla_days
    """)
    overdue_complaints_count = cursor.fetchone().overdue_complaints_count

    # الشكاوى ضمن المهلة
    cursor.execute("""
        SELECT COUNT(*) AS on_time_complaints_count
        FROM Complaints
        JOIN Departments ON Complaints.department_id = Departments.department_id
        WHERE Complaints.status IN ('Pending', 'In Progress')
          AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) <= Departments.sla_days
    """)
    on_time_complaints_count = cursor.fetchone().on_time_complaints_count

    conn.close()

    return render_template(
        "admin_dashboard.html",
        full_name=full_name,
        total_employees=total_employees,
        total_students=total_students,
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints,
        cancelled_complaints=cancelled_complaints,
        average_rating=average_rating,
        rated_complaints_count=rated_complaints_count,
        overdue_complaints_count=overdue_complaints_count,
        on_time_complaints_count=on_time_complaints_count
    )

#اضافة موظف جديد من قبل الادمن 
@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    message = ""

    # الأقسام الأساسية فقط
    cursor.execute("""
        SELECT department_id, department_name
        FROM Departments
        WHERE department_name IN ('الشؤون الأكاديمية', 'المالية', 'شؤون الطلاب', 'تقنية المعلومات')
        ORDER BY department_id
    """)
    departments = cursor.fetchall()

    # جميع الوحدات الفرعية
    cursor.execute("""
        SELECT unit_id, base_department_id, unit_name, stage_number
        FROM Department_Units
        ORDER BY base_department_id, stage_number
    """)
    units = cursor.fetchall()

    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        department_id = int(request.form["department_id"])
        unit_id = int(request.form["unit_id"])

        hashed_password = generate_password_hash(password)

        # نتأكد أن الوحدة المختارة تتبع القسم المختار
        cursor.execute("""
            SELECT unit_id
            FROM Department_Units
            WHERE unit_id = ? AND base_department_id = ?
        """, (unit_id, department_id))
        valid_unit = cursor.fetchone()

        if not valid_unit:
            message = "الوحدة المختارة لا تتبع القسم الأساسي المحدد."
        else:
            cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                message = "هذا البريد الإلكتروني مستخدم مسبقًا"
            else:
                cursor.execute("""
                    INSERT INTO Users (full_name, email, password, role, department_id, unit_id, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (full_name, email, hashed_password, "employee", department_id, unit_id, 1))
                conn.commit()
                message = "تمت إضافة الموظف بنجاح"

    conn.close()

    return render_template(
        "add_employee.html",
        departments=departments,
        units=units,
        message=message
    )


#تقديم شكوى جديدة من قبل الطالب مع مرفق اختياري
@app.route("/add_complaint", methods=["GET", "POST"])
def add_complaint():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    message = ""
    similar_complaints = []
    warning_message = ""
    require_confirmation = False

    form_data = {
        "category_id": "",
        "title": "",
        "description": ""
    }

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category_id, category_name
        FROM Complaint_Categories
        ORDER BY category_id ASC
    """)
    categories = cursor.fetchall()

    if request.method == "POST":
        action = request.form.get("action")

        category_id = request.form["category_id"]
        title = request.form["title"]
        description = request.form["description"]

        form_data["category_id"] = category_id
        form_data["title"] = title
        form_data["description"] = description

        new_text = f"{title} {description}"

        cursor.execute("""
            SELECT complaint_id, title, description, status
            FROM Complaints
            WHERE category_id = ? AND status != 'Cancelled'
        """, (category_id,))
        existing_complaints = cursor.fetchall()

        results = []

        for complaint in existing_complaints:
            old_text = f"{complaint.title} {complaint.description}"
            similarity = calculate_similarity(new_text, old_text)

            if similarity >= 0.40:
                results.append({
                    "complaint_id": complaint.complaint_id,
                    "title": complaint.title,
                    "status": complaint.status,
                    "similarity_percent": round(similarity * 100, 1)
                })

        results.sort(key=lambda x: x["similarity_percent"], reverse=True)
        similar_complaints = results[:3]

        highest_similarity = similar_complaints[0] if similar_complaints else None

        if action == "check_similarity":
            if similar_complaints:
                message = "تم العثور على شكاوى مشابهة. راجعيها قبل الإرسال."

                if highest_similarity["status"] == "Resolved":
                    warning_message = "توجد شكوى مشابهة تم حلها سابقًا، وقد تكون المشكلة نفسها قد تمت معالجتها."
                elif highest_similarity["status"] in ["Pending", "In Progress"]:
                    warning_message = "توجد شكوى مشابهة قيد المعالجة حاليًا، وقد تكون مشكلتك نفسها قيد المتابعة الآن."

                if highest_similarity["similarity_percent"] >= 85:
                    require_confirmation = True
            else:
                message = "لم يتم العثور على شكاوى مشابهة واضحة. يمكنك إرسال الشكوى."

        elif action == "submit_complaint":
            confirmed = request.form.get("confirmed_submission")

            if highest_similarity and highest_similarity["similarity_percent"] >= 85 and confirmed != "yes":
                message = "تم العثور على شكوى مشابهة جدًا. إذا كنت تريد المتابعة فعلًا، اضغط على زر التأكيد."
                warning_message = "يوجد تشابه مرتفع جدًا مع شكوى سابقة، لذلك نطلب منك تأكيدًا إضافيًا قبل الإرسال."
                require_confirmation = True
            else:
                student_id = session.get("user_id")

                cursor.execute("""
                    SELECT department_id
                    FROM Complaint_Categories
                    WHERE category_id = ?
                """, (category_id,))
                category = cursor.fetchone()

                department_id = category.department_id

                cursor.execute("""
                    SELECT unit_id
                    FROM Department_Units
                    WHERE base_department_id = ? AND stage_number = 1
                """, (department_id,))
                first_unit = cursor.fetchone()

                cursor.execute("""
                    SELECT stage_id
                    FROM Department_Processing_Stages
                    WHERE base_department_id = ? AND stage_number = 1
                """, (department_id,))
                first_stage = cursor.fetchone()

                current_unit_id = first_unit.unit_id
                current_stage_id = first_stage.stage_id if first_stage else None

                cursor.execute("""
                    INSERT INTO Complaints (
                        student_id, category_id, department_id, title, description, status,
                        current_stage, current_stage_id, current_unit_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id, category_id, department_id, title, description, "Pending",
                    1, current_stage_id, current_unit_id
                ))

                conn.commit()

                cursor.execute("SELECT TOP 1 complaint_id FROM Complaints ORDER BY complaint_id DESC")
                complaint = cursor.fetchone()
                complaint_id = complaint.complaint_id

                file = request.files.get("attachment")

                if file and file.filename != "":
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(file_path)

                    cursor.execute("""
                        INSERT INTO Attachments (complaint_id, file_name, file_path)
                        VALUES (?, ?, ?)
                    """, (complaint_id, filename, file_path))

                    conn.commit()

                message = "تم إرسال الشكوى بنجاح"
                warning_message = ""
                similar_complaints = []
                require_confirmation = False

                form_data = {
                    "category_id": "",
                    "title": "",
                    "description": ""
                }

    conn.close()

    return render_template(
        "add_complaint.html",
        message=message,
        warning_message=warning_message,
        categories=categories,
        similar_complaints=similar_complaints,
        form_data=form_data,
        require_confirmation=require_confirmation
    )

#عرض جميع شكاوى الطالب الحالي
@app.route("/my_complaints")
def my_complaints():
    if session.get("role") != "student": # هون بنتحقق من دور المستخدم في الجلسة، إذا ما كان دوره "student" بنعيد توجيهه إلى الصفحة الرئيسية (home) عشان ما يقدر يوصل إلى صفحة عرض شكاواه.
        return redirect(url_for("login"))
    complaints = []
    message = ""

    student_id = session.get("user_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT complaint_id, title, status, submitted_at
        FROM Complaints
        WHERE student_id = ?
    """, (student_id,))

    complaints = cursor.fetchall()
    conn.close()

    if not complaints:
        message = "لا توجد شكاوى لك حتى الآن"

    return render_template("my_complaints.html", complaints=complaints, message=message)

# عرض شكاوى القسم مع امكانية فلترة الشكاوى حسب الحالة او البحث عن شكوى معينة من قبل الموظف
@app.route("/department_complaints", methods=["GET"])
def department_complaints():
    if session.get("role") != "employee":
        return redirect(url_for("login"))

    unit_id = session.get("unit_id")
    selected_status = request.args.get("status")
    search_text = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT Complaints.complaint_id,
               Complaints.title,
               Complaints.status,
               Complaints.submitted_at,
               Complaints.current_stage,
               Department_Units.unit_name,
               Departments.sla_days,
               CASE
                   WHEN Complaints.status IN ('Pending', 'In Progress')
                        AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) > Departments.sla_days
                   THEN 1
                   ELSE 0
               END AS is_overdue
        FROM Complaints
        LEFT JOIN Department_Units
            ON Complaints.current_unit_id = Department_Units.unit_id
        LEFT JOIN Departments
            ON Complaints.department_id = Departments.department_id
        WHERE Complaints.current_unit_id = ? AND Complaints.status != 'Cancelled'
    """
    params = [unit_id]

    if selected_status:
        query += " AND Complaints.status = ?"
        params.append(selected_status)

    if search_text:
        if search_text.isdigit():
            query += " AND Complaints.complaint_id = ?"
            params.append(int(search_text))
        else:
            query += " AND Complaints.title LIKE ?"
            params.append(f"%{search_text}%")

    query += """
        ORDER BY
            CASE
                WHEN Complaints.status IN ('Pending', 'In Progress')
                     AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) > Departments.sla_days
                THEN 1
                WHEN Complaints.status = 'Pending' THEN 2
                WHEN Complaints.status = 'In Progress' THEN 3
                WHEN Complaints.status = 'Resolved' THEN 4
                ELSE 5
            END,
            Complaints.submitted_at ASC,
            Complaints.complaint_id ASC
    """

    cursor.execute(query, params)
    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "department_complaints.html",
        complaints=complaints,
        selected_status=selected_status,
        search_text=search_text
    )
# تسجيل الخروج من النظام، هون بنمسح بيانات الجلسة عشان نضمن ان المستخدم ما يظل مسجل دخوله بعد ما يضغط على زر تسجيل الخروج، وهذا بيزيد من أمان التطبيق ويمنع أي شخص آخر من الوصول إلى بيانات المستخدم بعد ما يسجل الخروج.
@app.route("/logout")
def logout():
    session.clear() # هون بنمسح كل بيانات الجلسة، يعني لما المستخدم يضغط على زر تسجيل الخروج، بنمسح كل المعلومات اللي مخزنة في الجلسة مثل user_id و full_name و role و department_id، عشان نضمن انه ما يظل فيه بيانات مستخدم بعد ما يسجل الخروج.
    return redirect(url_for("home")) # بعد ما مسحنا بيانات الجلسة، بنعيد توجيه المستخدم إلى الصفحة الرئيسية (home) باستخدام redirect و url_for.

#عرض تفاصيل  شكوى القسم مع الردود و امكانية تحديث الحالة او تحويل الشكوى لقسم اخر من قبل الموظف
@app.route("/complaint_details/<int:complaint_id>", methods=["GET", "POST"])
def complaint_details(complaint_id):
    if session.get("role") != "employee":
        return redirect(url_for("login"))

    employee_id = session.get("user_id")
    employee_department_id = session.get("department_id")
    employee_unit_id = session.get("unit_id")
    message = ""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT department_id, department_name
        FROM Departments
        WHERE department_name IN ('الشؤون الأكاديمية', 'المالية', 'شؤون الطلاب', 'تقنية المعلومات')
        ORDER BY department_id
    """)
    departments = cursor.fetchall()

    if request.method == "POST":
        action = request.form.get("action")

        cursor.execute("""
            SELECT Complaints.complaint_id,
                   Complaints.department_id,
                   Complaints.current_stage,
                   Complaints.current_stage_id,
                   Complaints.current_unit_id,
                   Complaints.status,
                   Department_Units.unit_name
            FROM Complaints
            LEFT JOIN Department_Units
                ON Complaints.current_unit_id = Department_Units.unit_id
            WHERE Complaints.complaint_id = ?
        """, (complaint_id,))
        current_complaint = cursor.fetchone()

        if not current_complaint:
            conn.close()
            return redirect(url_for("department_complaints"))

        if current_complaint.current_unit_id != employee_unit_id:
            conn.close()
            return redirect(url_for("department_complaints"))

        # منع أي تعديل على الشكاوى المحلولة أو الملغاة
        if current_complaint.status in ["Resolved", "Cancelled"]:
            message = "لا يمكن تعديل أو تحويل أو معالجة شكوى محلولة أو ملغاة"
        else:
            if action == "update_status":
                response_text = request.form.get("response_text")
                new_status = request.form["status"]

                if response_text and response_text.strip() != "":
                    cursor.execute("""
                        INSERT INTO Complaint_Responses (complaint_id, employee_id, response_text)
                        VALUES (?, ?, ?)
                    """, (complaint_id, employee_id, response_text))

                cursor.execute("""
                    UPDATE Complaints
                    SET status = ?
                    WHERE complaint_id = ?
                """, (new_status, complaint_id))

                conn.commit()
                message = "تم تحديث الحالة بنجاح"

            elif action == "transfer_department":
                new_department_id = int(request.form["new_department_id"])
                note = request.form.get("transfer_note", "").strip()

                cursor.execute("""
                    SELECT unit_id
                    FROM Department_Units
                    WHERE base_department_id = ? AND stage_number = 1
                """, (new_department_id,))
                first_unit = cursor.fetchone()

                cursor.execute("""
                    SELECT stage_id
                    FROM Department_Processing_Stages
                    WHERE base_department_id = ? AND stage_number = 1
                """, (new_department_id,))
                first_stage = cursor.fetchone()

                if first_unit:
                    old_department_id = current_complaint.department_id
                    old_stage = current_complaint.current_stage

                    cursor.execute("""
                        UPDATE Complaints
                        SET department_id = ?, current_stage = 1, current_stage_id = ?, current_unit_id = ?, status = ?
                        WHERE complaint_id = ?
                    """, (
                        new_department_id,
                        first_stage.stage_id if first_stage else None,
                        first_unit.unit_id,
                        "Pending",
                        complaint_id
                    ))

                    cursor.execute("""
                        INSERT INTO Complaint_Processing_Log
                        (complaint_id, from_stage, to_stage, from_department_id, to_department_id, handled_by_user_id, action_type, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        complaint_id,
                        old_stage,
                        1,
                        old_department_id,
                        new_department_id,
                        employee_id,
                        'transfer',
                        note if note else 'تم تحويل الشكوى إلى قسم أساسي آخر'
                    ))

                    conn.commit()
                    message = "تم تحويل الشكوى إلى القسم الجديد وإعادتها للمرحلة الأولى"
                else:
                    message = "تعذر تحديد أول وحدة في القسم الجديد"

            elif action == "next_stage":
                note = request.form.get("stage_note", "").strip()
                current_stage = current_complaint.current_stage
                base_department_id = current_complaint.department_id

                next_stage = current_stage + 1

                cursor.execute("""
                    SELECT unit_id, unit_name
                    FROM Department_Units
                    WHERE base_department_id = ? AND stage_number = ?
                """, (base_department_id, next_stage))
                next_unit = cursor.fetchone()

                cursor.execute("""
                    SELECT stage_id
                    FROM Department_Processing_Stages
                    WHERE base_department_id = ? AND stage_number = ?
                """, (base_department_id, next_stage))
                next_stage_row = cursor.fetchone()

                if next_unit:
                    cursor.execute("""
                        UPDATE Complaints
                        SET current_stage = ?, current_stage_id = ?, current_unit_id = ?, status = ?
                        WHERE complaint_id = ?
                    """, (
                        next_stage,
                        next_stage_row.stage_id if next_stage_row else None,
                        next_unit.unit_id,
                        "In Progress",
                        complaint_id
                    ))

                    cursor.execute("""
                        INSERT INTO Complaint_Processing_Log
                        (complaint_id, from_stage, to_stage, from_department_id, to_department_id, handled_by_user_id, action_type, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        complaint_id,
                        current_stage,
                        next_stage,
                        base_department_id,
                        base_department_id,
                        employee_id,
                        'forward',
                        note
                    ))

                    conn.commit()
                    message = "تم إرسال الشكوى إلى المرحلة التالية بنجاح"
                else:
                    message = "لا توجد مرحلة تالية لهذه الشكوى"

            elif action == "previous_stage":
                note = request.form.get("stage_note", "").strip()
                current_stage = current_complaint.current_stage
                base_department_id = current_complaint.department_id

                previous_stage = current_stage - 1

                if previous_stage >= 1:
                    cursor.execute("""
                        SELECT unit_id, unit_name
                        FROM Department_Units
                        WHERE base_department_id = ? AND stage_number = ?
                    """, (base_department_id, previous_stage))
                    previous_unit = cursor.fetchone()

                    cursor.execute("""
                        SELECT stage_id
                        FROM Department_Processing_Stages
                        WHERE base_department_id = ? AND stage_number = ?
                    """, (base_department_id, previous_stage))
                    previous_stage_row = cursor.fetchone()

                    if previous_unit:
                        cursor.execute("""
                            UPDATE Complaints
                            SET current_stage = ?, current_stage_id = ?, current_unit_id = ?, status = ?
                            WHERE complaint_id = ?
                        """, (
                            previous_stage,
                            previous_stage_row.stage_id if previous_stage_row else None,
                            previous_unit.unit_id,
                            "In Progress",
                            complaint_id
                        ))

                        cursor.execute("""
                            INSERT INTO Complaint_Processing_Log
                            (complaint_id, from_stage, to_stage, from_department_id, to_department_id, handled_by_user_id, action_type, note)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            complaint_id,
                            current_stage,
                            previous_stage,
                            base_department_id,
                            base_department_id,
                            employee_id,
                            'backward',
                            note
                        ))

                        conn.commit()
                        message = "تم إرجاع الشكوى إلى المرحلة السابقة بنجاح"
                    else:
                        message = "تعذر تحديد المرحلة السابقة"
                else:
                    message = "هذه الشكوى موجودة بالفعل في المرحلة الأولى"

    cursor.execute("""
        SELECT Complaints.complaint_id,
               Complaints.title,
               Complaints.description,
               Complaints.status,
               Complaints.submitted_at,
               Complaints.current_stage,
               Users.full_name AS student_name,
               Users.user_id AS student_id,
               Departments.department_name,
               Departments.sla_days,
               Complaint_Categories.category_name,
               Department_Units.unit_name AS stage_name
        FROM Complaints
        JOIN Users ON Complaints.student_id = Users.user_id
        JOIN Departments ON Complaints.department_id = Departments.department_id
        JOIN Complaint_Categories ON Complaints.category_id = Complaint_Categories.category_id
        LEFT JOIN Department_Units
            ON Complaints.current_unit_id = Department_Units.unit_id
        WHERE Complaints.complaint_id = ?
    """, (complaint_id,))
    complaint = cursor.fetchone()

    is_overdue = False

    if complaint and complaint.sla_days and complaint.status in ["Pending", "In Progress"]:
        submitted_date = complaint.submitted_at
        if isinstance(submitted_date, str):
            submitted_date = datetime.fromisoformat(submitted_date)
        days_passed = (datetime.now() - submitted_date).days
        if days_passed > complaint.sla_days:
            is_overdue = True

    cursor.execute("""
        SELECT response_text, response_date
        FROM Complaint_Responses
        WHERE complaint_id = ?
        ORDER BY response_date DESC
    """, (complaint_id,))
    responses = cursor.fetchall()

    cursor.execute("""
        SELECT file_name, file_path
        FROM Attachments
        WHERE complaint_id = ?
    """, (complaint_id,))
    attachments = cursor.fetchall()

    cursor.execute("""
        SELECT log.log_id,
               log.from_stage,
               log.to_stage,
               log.action_type,
               log.note,
               log.action_date,
               from_dept.department_name AS from_department_name,
               to_dept.department_name AS to_department_name,
               Users.full_name AS handled_by_name
        FROM Complaint_Processing_Log AS log
        LEFT JOIN Departments AS from_dept ON log.from_department_id = from_dept.department_id
        LEFT JOIN Departments AS to_dept ON log.to_department_id = to_dept.department_id
        LEFT JOIN Users ON log.handled_by_user_id = Users.user_id
        WHERE log.complaint_id = ?
        ORDER BY log.action_date DESC
    """, (complaint_id,))
    processing_logs = cursor.fetchall()

    # جلب تقييم الطالب إن وجد لعرضه للموظف
    feedback = None
    if complaint:
        cursor.execute("""
            SELECT rating, feedback_note, feedback_date
            FROM Complaint_Feedback
            WHERE complaint_id = ? AND student_id = ?
        """, (complaint_id, complaint.student_id))
        feedback = cursor.fetchone()

    conn.close()

    return render_template(
        "complaint_details.html",
        complaint=complaint,
        message=message,
        departments=departments,
        responses=responses,
        attachments=attachments,
        processing_logs=processing_logs,
        is_overdue=is_overdue,
        feedback=feedback
    )

#عرض تفاصيل  شكوى الطالب مع الردود و التعليقات و المرفقات و امكانية اضافة تعليق جديد او مرفق  جديد 
@app.route("/student_complaint_details/<int:complaint_id>", methods=["GET", "POST"])
def student_complaint_details(complaint_id):
    if session.get("role") != "student":
        return redirect(url_for("login"))

    student_id = session.get("user_id")
    message = ""

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        cursor.execute("""
            SELECT status
            FROM Complaints
            WHERE complaint_id = ? AND student_id = ?
        """, (complaint_id, student_id))
        current_status_row = cursor.fetchone()
        current_status = current_status_row.status if current_status_row else None

        if action == "add_comment":
            if current_status in ["Resolved", "Cancelled"]:
                message = "لا يمكن إضافة تعليق بعد إغلاق الشكوى"
            else:
                comment_text = request.form.get("comment_text")

                if comment_text and comment_text.strip() != "":
                    cursor.execute("""
                        INSERT INTO Complaint_Comments (complaint_id, student_id, comment_text)
                        VALUES (?, ?, ?)
                    """, (complaint_id, student_id, comment_text))
                    conn.commit()
                    message = "تمت إضافة تعليقك بنجاح"

        elif action == "add_attachment":
            if current_status in ["Resolved", "Cancelled"]:
                message = "لا يمكن رفع ملف بعد إغلاق الشكوى"
            else:
                file = request.files.get("new_attachment")

                if file and file.filename != "":
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(file_path)

                    cursor.execute("""
                        INSERT INTO Attachments (complaint_id, file_name, file_path)
                        VALUES (?, ?, ?)
                    """, (complaint_id, filename, file_path))
                    conn.commit()
                    message = "تم رفع الملف بنجاح"

        elif action == "add_feedback":
            rating = int(request.form["rating"])
            feedback_note = request.form.get("feedback_note", "").strip()

            cursor.execute("""
                SELECT feedback_id
                FROM Complaint_Feedback
                WHERE complaint_id = ? AND student_id = ?
            """, (complaint_id, student_id))
            existing_feedback = cursor.fetchone()

            if existing_feedback:
                message = "لقد قمت بتقييم هذه الشكوى مسبقًا"
            else:
                if current_status == "Resolved":
                    cursor.execute("""
                        INSERT INTO Complaint_Feedback (complaint_id, student_id, rating, feedback_note)
                        VALUES (?, ?, ?, ?)
                    """, (complaint_id, student_id, rating, feedback_note))
                    conn.commit()
                    message = "تم إرسال تقييمك بنجاح"
                else:
                    message = "لا يمكن تقييم الشكوى قبل حلها"

    cursor.execute("""
        SELECT Complaints.complaint_id,
               Complaints.title,
               Complaints.description,
               Complaints.status,
               Complaints.submitted_at,
               Complaints.current_stage,
               Departments.department_name,
               Departments.sla_days,
               Complaint_Categories.category_name,
               Department_Units.unit_name AS stage_name
        FROM Complaints
        JOIN Departments ON Complaints.department_id = Departments.department_id
        JOIN Complaint_Categories ON Complaints.category_id = Complaint_Categories.category_id
        LEFT JOIN Department_Units
            ON Complaints.current_unit_id = Department_Units.unit_id
        WHERE Complaints.complaint_id = ? AND Complaints.student_id = ?
    """, (complaint_id, student_id))

    complaint = cursor.fetchone()

    is_overdue = False

    if complaint and complaint.sla_days and complaint.status in ["Pending", "In Progress"]:
        submitted_date = complaint.submitted_at
        if isinstance(submitted_date, str):
            submitted_date = datetime.fromisoformat(submitted_date)
        days_passed = (datetime.now() - submitted_date).days
        if days_passed > complaint.sla_days:
            is_overdue = True

    cursor.execute("""
        SELECT response_text, response_date
        FROM Complaint_Responses
        WHERE complaint_id = ?
        ORDER BY response_date DESC
    """, (complaint_id,))
    responses = cursor.fetchall()

    cursor.execute("""
        SELECT comment_text, comment_date
        FROM Complaint_Comments
        WHERE complaint_id = ? AND student_id = ?
        ORDER BY comment_date DESC
    """, (complaint_id, student_id))
    comments = cursor.fetchall()

    cursor.execute("""
        SELECT file_name, file_path
        FROM Attachments
        WHERE complaint_id = ?
    """, (complaint_id,))
    attachments = cursor.fetchall()

    cursor.execute("""
        SELECT log.log_id,
               log.from_stage,
               log.to_stage,
               log.action_type,
               log.note,
               log.action_date,
               from_dept.department_name AS from_department_name,
               to_dept.department_name AS to_department_name
        FROM Complaint_Processing_Log AS log
        LEFT JOIN Departments AS from_dept ON log.from_department_id = from_dept.department_id
        LEFT JOIN Departments AS to_dept ON log.to_department_id = to_dept.department_id
        WHERE log.complaint_id = ?
        ORDER BY log.action_date DESC
    """, (complaint_id,))
    processing_logs = cursor.fetchall()

    cursor.execute("""
        SELECT rating, feedback_note, feedback_date
        FROM Complaint_Feedback
        WHERE complaint_id = ? AND student_id = ?
    """, (complaint_id, student_id))
    feedback = cursor.fetchone()

    conn.close()

    return render_template(
        "student_complaint_details.html",
        complaint=complaint,
        responses=responses,
        comments=comments,
        attachments=attachments,
        processing_logs=processing_logs,
        feedback=feedback,
        message=message,
        is_overdue=is_overdue
    )

#عرض الموظفين الحاليين من قبل الادمن
@app.route("/view_employees")
def view_employees():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Departments.department_id,
               Departments.department_name,
               Department_Units.unit_id,
               Department_Units.unit_name,
               Department_Units.stage_number,
               Users.user_id,
               Users.full_name,
               Users.email,
               Users.is_active
        FROM Departments
        LEFT JOIN Department_Units
            ON Department_Units.base_department_id = Departments.department_id
        LEFT JOIN Users
            ON Users.unit_id = Department_Units.unit_id
           AND Users.role = 'employee'
        WHERE Departments.department_name IN ('الشؤون الأكاديمية', 'المالية', 'شؤون الطلاب', 'تقنية المعلومات')
        ORDER BY Departments.department_id, Department_Units.stage_number, Users.full_name
    """)

    rows = cursor.fetchall()
    conn.close()

    grouped_departments = []
    current_department_id = None
    current_department = None
    current_unit_id = None
    current_unit = None

    for row in rows:
        if row.department_id != current_department_id:
            current_department = {
                "department_id": row.department_id,
                "department_name": row.department_name,
                "units": []
            }
            grouped_departments.append(current_department)
            current_department_id = row.department_id
            current_unit_id = None

        if row.unit_id != current_unit_id:
            current_unit = {
                "unit_id": row.unit_id,
                "unit_name": row.unit_name,
                "stage_number": row.stage_number,
                "employees": []
            }
            current_department["units"].append(current_unit)
            current_unit_id = row.unit_id

        if row.user_id is not None:
            current_unit["employees"].append({
                "user_id": row.user_id,
                "full_name": row.full_name,
                "email": row.email,
                "is_active": row.is_active
            })

    return render_template("view_employees.html", departments=grouped_departments)

#تفعيل او تعطيل حساب الموظف من قبل الادمن 
@app.route("/toggle_employee_status/<int:user_id>", methods=["POST"]) # روت لتفعيل أو تعطيل حساب الموظف، هون بنستخدم POST عشان نضمن ان العملية تتم عن طريق ارسال بيانات من نموذج وليس عن طريق رابط مباشر، وهذا بيزيد من الأمان ويمنع التلاعب في الروابط.
def toggle_employee_status(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT is_active FROM Users WHERE user_id = ?", (user_id,))
    employee = cursor.fetchone()

    if employee:
        new_status = 0 if employee.is_active == 1 else 1

        cursor.execute("""
            UPDATE Users
            SET is_active = ?
            WHERE user_id = ?
        """, (new_status, user_id))

        conn.commit()

    conn.close()

    return redirect(url_for("view_employees"))

# إلغاء الشكوى من قبل الطالب في حالة الانتظار فقط
@app.route("/cancel_complaint/<int:complaint_id>", methods=["POST"])
def cancel_complaint(complaint_id):
    if session.get("role") != "student":
        return redirect(url_for("login"))

    student_id = session.get("user_id") # جلب الطالب الحالي من الجلسة عشان نستخدمه في عملية إلغاء الشكوى، هون بنستخدم session.get("user_id") عشان نجيب معرف الطالب اللي مسجل الدخول حالياً، وهذا ضروري عشان نضمن ان الطالب يقدر يلغي فقط شكاواه الخاصة به وما يقدر يلغي شكاوى طلاب آخرين.

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Complaints
        SET status = 'Cancelled'
        WHERE complaint_id = ? AND student_id = ? AND status = 'Pending'
    """, (complaint_id, student_id))

    conn.commit()
    conn.close()

    return redirect(url_for("my_complaints"))

#فتح او تحميل ملف مرفوع من مجلد الويبلودز
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

#اضافة قسم جديد من قبل الادمن + يتاكد ان المستخدم هو الادمن + يسمح بادخال اسم القسم + يمنع التكرار + يعرض رسالة نجاح أو خطأ
@app.route("/manage_departments", methods=["GET", "POST"])
def manage_departments():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    message = ""

    if request.method == "POST":
        department_name = request.form["department_name"].strip()
        stage1_name = request.form["stage1_name"].strip()
        stage2_name = request.form["stage2_name"].strip()
        stage3_name = request.form["stage3_name"].strip()
        sla_days = int(request.form["sla_days"])

        cursor.execute("""
            SELECT department_id
            FROM Departments
            WHERE department_name = ?
        """, (department_name,))
        existing_department = cursor.fetchone()

        if existing_department:
            message = "هذا القسم موجود مسبقًا."
        else:
            cursor.execute("""
                INSERT INTO Departments (department_name, sla_days)
                VALUES (?, ?)
            """, (department_name, sla_days))
            conn.commit()

            cursor.execute("""
                SELECT TOP 1 department_id
                FROM Departments
                ORDER BY department_id DESC
            """)
            new_department = cursor.fetchone()
            new_department_id = new_department.department_id

            cursor.execute("""
                INSERT INTO Department_Units (base_department_id, unit_name, stage_number)
                VALUES (?, ?, ?)
            """, (new_department_id, stage1_name, 1))

            cursor.execute("""
                INSERT INTO Department_Units (base_department_id, unit_name, stage_number)
                VALUES (?, ?, ?)
            """, (new_department_id, stage2_name, 2))

            cursor.execute("""
                INSERT INTO Department_Units (base_department_id, unit_name, stage_number)
                VALUES (?, ?, ?)
            """, (new_department_id, stage3_name, 3))

            conn.commit()
            message = "تمت إضافة القسم والمراحل ومدة المعالجة بنجاح"

    cursor.execute("""
        SELECT department_id, department_name, sla_days
        FROM Departments
        WHERE department_id NOT IN (1002,1003)
        ORDER BY department_id
    """)
    departments = cursor.fetchall()

    conn.close()

    return render_template(
        "manage_departments.html",
        departments=departments,
        message=message
    )

#اضافة تصنيف جديد من قبل الادمن + يتاكد ان المستخدم هو الادمن + يسمح بادخال اسم التصنيف + يربطه بقسم معين + يمنع التكرار + يعرض رسالة نجاح أو خطأ
@app.route("/manage_categories", methods=["GET", "POST"])
def manage_categories():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    message = ""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT department_id, department_name
        FROM Departments
        WHERE department_id NOT IN (1002,1003)
        ORDER BY department_id 
    """)
    departments = cursor.fetchall()

    if request.method == "POST":
        category_name = request.form["category_name"]
        department_id = request.form["department_id"]

        cursor.execute("""
            SELECT * FROM Complaint_Categories
            WHERE category_name = ?
        """, (category_name,))
        existing_category = cursor.fetchone()

        if existing_category:
            message = "هذا التصنيف موجود مسبقًا"
        else:
            cursor.execute("""
                INSERT INTO Complaint_Categories (category_name, department_id)
                VALUES (?, ?)
            """, (category_name, department_id))
            conn.commit()
            message = "تمت إضافة التصنيف بنجاح"

    cursor.execute("""
        SELECT Complaint_Categories.category_id,
               Complaint_Categories.category_name,
               Departments.department_name
        FROM Complaint_Categories
        JOIN Departments ON Complaint_Categories.department_id = Departments.department_id
        ORDER BY Complaint_Categories.category_id ASC
    """)
    categories = cursor.fetchall()

    conn.close()

    return render_template(
        "manage_categories.html",
        categories=categories,
        departments=departments,
        message=message
    )

#تعديل اسم قسم موجود من قبل الادمن + يتاكد ان المستخدم هو الادمن + يعرض اسم القسم الحالي + يسمح بالتعديل +يمنع التكرار + يعرض رسالة نجاح أو خطأ
@app.route("/edit_department/<int:department_id>", methods=["GET", "POST"])
def edit_department(department_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    message = ""

    if request.method == "POST":
        department_name = request.form["department_name"].strip()
        stage1_name = request.form["stage1_name"].strip()
        stage2_name = request.form["stage2_name"].strip()
        stage3_name = request.form["stage3_name"].strip()
        sla_days = int(request.form["sla_days"])

        cursor.execute("""
            UPDATE Departments
            SET department_name = ?, sla_days = ?
            WHERE department_id = ?
        """, (department_name, sla_days, department_id))

        cursor.execute("""
            UPDATE Department_Units
            SET unit_name = ?
            WHERE base_department_id = ? AND stage_number = 1
        """, (stage1_name, department_id))

        cursor.execute("""
            UPDATE Department_Units
            SET unit_name = ?
            WHERE base_department_id = ? AND stage_number = 2
        """, (stage2_name, department_id))

        cursor.execute("""
            UPDATE Department_Units
            SET unit_name = ?
            WHERE base_department_id = ? AND stage_number = 3
        """, (stage3_name, department_id))

        conn.commit()
        message = "تم تعديل القسم والمراحل ومدة المعالجة بنجاح"

    cursor.execute("""
        SELECT department_name, sla_days
        FROM Departments
        WHERE department_id = ?
    """, (department_id,))
    department = cursor.fetchone()

    cursor.execute("""
        SELECT stage_number, unit_name
        FROM Department_Units
        WHERE base_department_id = ?
        ORDER BY stage_number
    """, (department_id,))
    stages = cursor.fetchall()

    conn.close()

    stage1 = stage2 = stage3 = ""
    for s in stages:
        if s.stage_number == 1:
            stage1 = s.unit_name
        elif s.stage_number == 2:
            stage2 = s.unit_name
        elif s.stage_number == 3:
            stage3 = s.unit_name

    return render_template(
        "edit_department.html",
        department=department,
        department_id=department_id,
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        message=message
    )

#تعديل اسم تصنيف موجود من قبل الادمن + يتاكد ان المستخدم هو الادمن + يعرض اسم التصنيف الحالي + يسمح بالتعديل +يمنع التكرار + يعرض رسالة نجاح أو خطأ 
@app.route("/edit_category/<int:category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    message = ""

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        new_name = request.form["category_name"]

        cursor.execute("""
            SELECT * FROM Complaint_Categories
            WHERE category_name = ? AND category_id != ?
        """, (new_name, category_id))
        existing_category = cursor.fetchone()

        if existing_category:
            message = "يوجد تصنيف آخر بنفس الاسم"
        else:
            cursor.execute("""
                UPDATE Complaint_Categories
                SET category_name = ?
                WHERE category_id = ?
            """, (new_name, category_id))
            conn.commit()
            message = "تم تعديل اسم التصنيف بنجاح"

    cursor.execute("""
        SELECT category_id, category_name
        FROM Complaint_Categories
        WHERE category_id = ?
    """, (category_id,))
    category = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_category.html",
        category=category,
        message=message
    )

#يجمع بيانات كل قسم في صف واحد 
@app.route("/complaints_analysis")
def complaints_analysis():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Departments.department_id,
            Departments.department_name,

            COUNT(DISTINCT CASE WHEN Users.role = 'employee' THEN Users.user_id END) AS total_employees,
            COUNT(DISTINCT Complaints.complaint_id) AS total_complaints,

            COUNT(DISTINCT CASE WHEN Complaints.status = 'Pending' THEN Complaints.complaint_id END) AS pending_complaints,
            COUNT(DISTINCT CASE WHEN Complaints.status = 'In Progress' THEN Complaints.complaint_id END) AS in_progress_complaints,
            COUNT(DISTINCT CASE WHEN Complaints.status = 'Resolved' THEN Complaints.complaint_id END) AS resolved_complaints,
            COUNT(DISTINCT CASE WHEN Complaints.status = 'Cancelled' THEN Complaints.complaint_id END) AS cancelled_complaints,

            COUNT(DISTINCT Complaint_Feedback.feedback_id) AS rated_complaints_count,
            AVG(CAST(Complaint_Feedback.rating AS FLOAT)) AS average_rating,

            COUNT(DISTINCT CASE
                WHEN Complaints.status IN ('Pending', 'In Progress')
                 AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) > Departments.sla_days
                THEN Complaints.complaint_id
            END) AS overdue_complaints_count,

            COUNT(DISTINCT CASE
                WHEN Complaints.status IN ('Pending', 'In Progress')
                 AND DATEDIFF(DAY, Complaints.submitted_at, GETDATE()) <= Departments.sla_days
                THEN Complaints.complaint_id
            END) AS on_time_complaints_count

        FROM Departments
        LEFT JOIN Users
            ON Users.department_id = Departments.department_id
           AND Users.role = 'employee'
        LEFT JOIN Complaints
            ON Complaints.department_id = Departments.department_id
        LEFT JOIN Complaint_Feedback
            ON Complaint_Feedback.complaint_id = Complaints.complaint_id

        WHERE Departments.department_id NOT IN (1002, 1003)

        GROUP BY Departments.department_id, Departments.department_name, Departments.sla_days
        ORDER BY Departments.department_id ASC
    """)

    departments_analysis = cursor.fetchall()
    conn.close()

    return render_template(
        "complaints_analysis.html",
        departments_analysis=departments_analysis
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

