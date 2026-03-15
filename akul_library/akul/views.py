from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Author, Publisher, Book, Student, Circulation, Penalty, LibrarySettings, Notification
from django.contrib import messages
from django.db import IntegrityError
from django.db import connection
from django.core.management.color import no_style
from datetime import date, datetime, timedelta
import json
from django.db.models import Sum, Count, Q
from django.http import FileResponse
import io
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

def get_library_settings():
    settings_obj = LibrarySettings.objects.first()
    if not settings_obj:
        # Create default settings if none exist
        settings_obj = LibrarySettings.objects.create()
    return settings_obj

def get_notifications():
    return Notification.objects.all().order_by('-created_at')[:50]

def add_notification(message):
    Notification.objects.create(message=message)
    
    # Keep only last 50 notifications
    count = Notification.objects.count()
    if count > 50:
        # Get IDs of the newest 50
        last_50_ids = Notification.objects.order_by('-created_at').values_list('id', flat=True)[:50]
        # Delete the rest
        Notification.objects.exclude(id__in=list(last_50_ids)).delete()

# Create your views here.

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            return render(request, 'admin_login.html', {'error': 'Invalid credentials'})
    return render(request, 'admin_login.html')

def admin_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password == confirm_password:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, email=email, password=password)
                return redirect('admin_login')
    return render(request, 'admin_register.html')

def generate_circulation_report(request):
    if not HAS_REPORTLAB:
        return HttpResponse("The 'reportlab' library is missing. Please install it using: pip install reportlab")

    # Filter logic (mirrors admin_dashboard)
    circ_search = request.GET.get('circ_search', '')
    circ_status = request.GET.get('circ_status', '')
    circ_sort = request.GET.get('circ_sort') or '-issue_date'
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    all_time = request.GET.get('all_time')

    circulations = Circulation.objects.all()

    if circ_search:
        circulations = circulations.filter(Q(student__name__icontains=circ_search) | Q(book__title__icontains=circ_search))
    
    if circ_status:
        if circ_status == 'overdue':
            circulations = circulations.filter(status='issued', due_date__lt=date.today())
        else:
            circulations = circulations.filter(status=circ_status)

    if not all_time:
        if start_date:
            circulations = circulations.filter(issue_date__gte=start_date)
        
        if end_date:
            circulations = circulations.filter(issue_date__lte=end_date)

    circulations = circulations.order_by(circ_sort, '-id')

    total_titles = Book.objects.count()
    total_copies = Book.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    available_copies = Book.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
    issued_copies = Circulation.objects.filter(status='issued').count()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    
    cell_style = ParagraphStyle('CellStyle', parent=normal_style, fontSize=9, leading=11, alignment=0)
    header_style = ParagraphStyle('HeaderStyle', parent=normal_style, fontSize=10, leading=12, textColor=colors.whitesmoke, fontName='Helvetica-Bold', alignment=1)

    elements.append(Paragraph("Circulation Report", title_style))
    elements.append(Spacer(1, 12))
    
    headers = ['Student', 'Book', 'Issue Date', 'Due Date', 'Return Date', 'Status', 'Fine']
    header_row = [Paragraph(h, header_style) for h in headers]
    data = [header_row]
    
    for circ in circulations:
        fine = f"{circ.fine_amount}" if circ.fine_amount else "-"
        return_date = circ.return_date.strftime('%Y-%m-%d') if circ.return_date else "-"
        
        row = [
            Paragraph(circ.student.name, cell_style),
            Paragraph(circ.book.title, cell_style),
            Paragraph(circ.issue_date.strftime('%Y-%m-%d'), cell_style),
            Paragraph(circ.due_date.strftime('%Y-%m-%d'), cell_style),
            Paragraph(return_date, cell_style),
            Paragraph(circ.status.title(), cell_style),
            Paragraph(fine, cell_style)
        ]
        data.append(row)
        
    col_widths = [100, 150, 65, 65, 65, 60, 40]
    
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    
    elements.append(PageBreak())
    elements.append(Paragraph("Library Statistics", title_style))
    elements.append(Spacer(1, 20))
    
    stats_data = [
        [Paragraph("Metric", header_style), Paragraph("Count", header_style)],
        [Paragraph("Total Book Titles", cell_style), Paragraph(str(total_titles), cell_style)],
        [Paragraph("Total Physical Books", cell_style), Paragraph(str(total_copies), cell_style)],
        [Paragraph("Books Available", cell_style), Paragraph(str(available_copies), cell_style)],
        [Paragraph("Books Issued", cell_style), Paragraph(str(issued_copies), cell_style)],
    ]
    
    stats_table = Table(stats_data, colWidths=[250, 100], hAlign='LEFT')
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(stats_table)
    
    elements.append(PageBreak())
    elements.append(Paragraph("Book Inventory Details", title_style))
    elements.append(Spacer(1, 12))

    inv_headers = ['Title', 'Author', 'ISBN', 'Total', 'Avail', 'Issued']
    inv_header_row = [Paragraph(h, header_style) for h in inv_headers]
    inv_data = [inv_header_row]

    all_books = Book.objects.all().order_by('title')

    for book in all_books:
        issued_qty = book.quantity - book.available_quantity
        row = [
            Paragraph(book.title, cell_style),
            Paragraph(book.author.name if book.author else "-", cell_style),
            Paragraph(book.isbn or "-", cell_style),
            Paragraph(str(book.quantity), cell_style),
            Paragraph(str(book.available_quantity), cell_style),
            Paragraph(str(issued_qty), cell_style),
        ]
        inv_data.append(row)
    
    inv_col_widths = [200, 120, 82, 50, 50, 50]
    inv_table = Table(inv_data, colWidths=inv_col_widths, repeatRows=1)
    inv_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(inv_table)

    doc.build(elements)
    
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='circulation_report.pdf')

def admin_dashboard(request):
    if request.GET.get('action') == 'generate_report':
        return generate_circulation_report(request)

    if request.method == 'POST' and 'notification_action' in request.POST:
        action = request.POST.get('notification_action')
        if action == 'clear':
            Notification.objects.all().delete()
        elif action == 'mark_read':
            Notification.objects.filter(read=False).update(read=True)
        elif action == 'mark_single_read':
            notification_id = request.POST.get('notification_id')
            if notification_id:
                Notification.objects.filter(id=notification_id).update(read=True)
        return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))

    search_query = request.GET.get('search_query', '')
    books = Book.objects.all().order_by('-id')
    
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__name__icontains=search_query) |
            Q(isbn__icontains=search_query)
        )

    circ_search = request.GET.get('circ_search', '')
    circ_status = request.GET.get('circ_status', '')
    circ_sort = request.GET.get('circ_sort') or '-issue_date'
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    all_time = request.GET.get('all_time')

    circulations = Circulation.objects.all()

    if circ_search:
        circulations = circulations.filter(Q(student__name__icontains=circ_search) | Q(book__title__icontains=circ_search))
    
    if circ_status:
        if circ_status == 'overdue':
            circulations = circulations.filter(status='issued', due_date__lt=date.today())
        else:
            circulations = circulations.filter(status=circ_status)

    if not all_time:
        if start_date:
            circulations = circulations.filter(issue_date__gte=start_date)
        
        if end_date:
            circulations = circulations.filter(issue_date__lte=end_date)

    circulations = circulations.order_by(circ_sort, '-id')

    total_students = Student.objects.count()
    issued_books_count = Circulation.objects.filter(status='issued').count()
    reserved_books_count = Book.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
    overdue_books_count = Circulation.objects.filter(status='issued', due_date__lt=date.today()).count()

    notifications = get_notifications()
    unread_count = Notification.objects.filter(read=False).count()

    chart_range = request.GET.get('chart_range', '6_months')
    chart_labels = []
    issue_counts = []
    student_counts = []
    revenue_data = []
    today = date.today()
    
    if chart_range == 'last_week':
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            chart_labels.append(d.strftime('%a'))
            issue_counts.append(Circulation.objects.filter(issue_date=d).count())
            student_counts.append(Student.objects.filter(joined_date__year=d.year, joined_date__month=d.month, joined_date__day=d.day).count())
            monthly_revenue = Penalty.objects.filter(created_at__year=d.year, created_at__month=d.month, created_at__day=d.day).aggregate(Sum('amount'))['amount__sum'] or 0
            revenue_data.append(float(monthly_revenue))
    elif chart_range == 'last_year':
        for i in range(11, -1, -1):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            chart_labels.append(date(y, m, 1).strftime('%b'))
            issue_counts.append(Circulation.objects.filter(issue_date__year=y, issue_date__month=m).count())
            student_counts.append(Student.objects.filter(joined_date__year=y, joined_date__month=m).count())
            monthly_revenue = Penalty.objects.filter(created_at__year=y, created_at__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
            revenue_data.append(float(monthly_revenue))
    else:
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            chart_labels.append(date(y, m, 1).strftime('%b'))
            issue_counts.append(Circulation.objects.filter(issue_date__year=y, issue_date__month=m).count())
            student_counts.append(Student.objects.filter(joined_date__year=y, joined_date__month=m).count())
            monthly_revenue = Penalty.objects.filter(created_at__year=y, created_at__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
            revenue_data.append(float(monthly_revenue))

    # Author Filtering and Sorting
    author_search = request.GET.get('author_search', '')
    author_sort = request.GET.get('author_sort', '-book_count')
    
    authors_qs = Author.objects.annotate(book_count=Count('book'))
    
    if author_search:
        authors_qs = authors_qs.filter(name__icontains=author_search)
        
    if author_sort == 'name_asc':
        authors_qs = authors_qs.order_by('name')
    elif author_sort == 'name_desc':
        authors_qs = authors_qs.order_by('-name')
    elif author_sort == 'book_count':
        authors_qs = authors_qs.order_by('book_count')
    else:
        authors_qs = authors_qs.order_by('-book_count')

    # Publisher Filtering and Sorting
    publisher_search = request.GET.get('publisher_search', '')
    publisher_sort = request.GET.get('publisher_sort', 'name_asc')
    
    publishers_qs = Publisher.objects.annotate(book_count=Count('book'))
    
    if publisher_search:
        publishers_qs = publishers_qs.filter(name__icontains=publisher_search)
        
    if publisher_sort == 'name_asc':
        publishers_qs = publishers_qs.order_by('name')
    elif publisher_sort == 'name_desc':
        publishers_qs = publishers_qs.order_by('-name')
    elif publisher_sort == 'book_count_desc':
        publishers_qs = publishers_qs.order_by('-book_count')
    elif publisher_sort == 'book_count_asc':
        publishers_qs = publishers_qs.order_by('book_count')
    else:
        publishers_qs = publishers_qs.order_by('name')

    # Student Filtering and Sorting
    student_search = request.GET.get('student_search', '')
    student_sort = request.GET.get('student_sort', '-joined_date')
    
    students_qs = Student.objects.all()
    
    if student_search:
        students_qs = students_qs.filter(Q(name__icontains=student_search) | Q(email__icontains=student_search))
        
    if student_sort == 'name_asc':
        students_qs = students_qs.order_by('name')
    elif student_sort == 'name_desc':
        students_qs = students_qs.order_by('-name')
    elif student_sort == 'joined_date_asc':
        students_qs = students_qs.order_by('joined_date')
    else:
        students_qs = students_qs.order_by('-joined_date')

    context = {
        'books': books,
        'search_query': search_query,
        'total_books': Book.objects.count(),
        'total_students': total_students,
        'issued_books_count': issued_books_count,
        'reserved_books_count': reserved_books_count,
        'overdue_books_count': overdue_books_count,
        'authors': authors_qs,
        'publishers': publishers_qs,
        'students': students_qs,
        'users': User.objects.all().order_by('-id'),
        'circulations': circulations,
        'recent_issued': Circulation.objects.filter(status='issued').order_by('-issue_date')[:5],
        'penalties': Penalty.objects.all(),
        'lib_settings': get_library_settings(),
        'notifications': notifications,
        'unread_count': unread_count,
        'chart_labels': json.dumps(chart_labels),
        'issue_counts': json.dumps(issue_counts),
        'student_counts': json.dumps(student_counts),
        'revenue_data': json.dumps(revenue_data),
    }
    return render(request, 'admin_library.html', context)

def admin_logout(request):
    logout(request)
    return redirect('admin_login')

def add_book(request):
    if request.method == "POST":
        title = request.POST.get('title')
        isbn = request.POST.get('isbn')
        total_qty = request.POST.get('total_quantity')
        avail_qty = request.POST.get('available_quantity')
        image_url = request.POST.get('image_url')
        
        # Handle Author (Select existing or Create new)
        author = None
        new_author_name = request.POST.get('new_author')
        if new_author_name:
            author, created = Author.objects.get_or_create(name=new_author_name)
        elif request.POST.get('author'):
            author = get_object_or_404(Author, id=request.POST.get('author'))

        if not author:
            add_notification("Failed to add book: Please select or enter an author.")
            return redirect(reverse('admin_dashboard') + '?tab=books')

        # Handle Publisher (Select existing or Create new)
        publisher = None
        new_publisher_name = request.POST.get('new_publisher')
        if new_publisher_name:
            publisher, created = Publisher.objects.get_or_create(name=new_publisher_name)
        elif request.POST.get('publisher'):
            publisher = get_object_or_404(Publisher, id=request.POST.get('publisher'))

        if not publisher:
            add_notification("Failed to add book: Please select or enter a publisher.")
            return redirect(reverse('admin_dashboard') + '?tab=books')
            
        if Book.objects.filter(isbn=isbn).exists():
            add_notification("Failed to add book: A book with this ISBN already exists.")
            return redirect(reverse('admin_dashboard') + '?tab=books')

        try:
            Book.objects.create(
                title=title, author=author, publisher=publisher, isbn=isbn,
                quantity=total_qty, available_quantity=avail_qty,
                thumbnail_link=image_url
            )
            add_notification(f"Book '{title}' added successfully.")
        except IntegrityError as e:
            if 'pkey' in str(e) or 'PRIMARY' in str(e):
                try:
                    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Book])
                    with connection.cursor() as cursor:
                        for sql in sequence_sql:
                            cursor.execute(sql)
                    Book.objects.create(
                        title=title, author=author, publisher=publisher, isbn=isbn,
                        quantity=total_qty, available_quantity=avail_qty,
                        thumbnail_link=image_url
                    )
                    add_notification(f"Book '{title}' added successfully (Database sequence repaired).")
                except Exception as retry_e:
                    add_notification(f"Error adding book: {e}. Retry failed: {retry_e}")
            else:
                add_notification(f"Error adding book: {e}")
        return redirect(reverse('admin_dashboard') + '?tab=books')
    return redirect('admin_dashboard')

def add_author(request):
    if request.method == "POST":
        name = request.POST.get('name')
        bio = request.POST.get('bio')
        if name:
            Author.objects.create(name=name, bio=bio)
        return redirect(reverse('admin_dashboard') + '?tab=authors')
    return redirect('admin_dashboard')

def add_publisher(request):
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            Publisher.objects.create(name=name)
        return redirect(reverse('admin_dashboard') + '?tab=publishers')
    return redirect('admin_dashboard')

def add_user(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        is_superuser = request.POST.get('is_superuser') == 'True'
        
        if username:
            if User.objects.filter(username=username).exists():
                add_notification(f"Error: Username '{username}' already exists.")
            else:
                try:
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.is_superuser = is_superuser
                    user.is_staff = is_superuser # Admins are usually staff
                    user.save()
                    add_notification(f"User '{username}' added successfully.")
                except Exception as e:
                    add_notification(f"Error adding user: {e}")
        return redirect(reverse('admin_dashboard') + '?tab=users')

def add_penalty(request):
    if request.method == "POST":
        student_input = request.POST.get('student')
        username_input = request.POST.get('username')
        amount = request.POST.get('amount')
        reason = request.POST.get('reason')
        book_title = request.POST.get('book_title')
        
        student = None
        if student_input and student_input.isdigit():
            student = Student.objects.filter(id=student_input).first()
            
        if not student and student_input:
            student = Student.objects.filter(name__iexact=student_input).first()
            
        if not student and username_input:
            student = Student.objects.filter(name__iexact=username_input).first()

        book = None
        if book_title:
            book = Book.objects.filter(title__iexact=book_title).first()

        if not reason and book_title:
            reason = f"Book: {book_title}"

        if student and amount:
            Penalty.objects.create(student=student, book=book, amount=amount, reason=reason or "Penalty")
        return redirect('admin_dashboard')

def add_student(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        Student.objects.create(name=name, email=email, phone=phone, address=address)
        return redirect(reverse('admin_dashboard') + '?tab=students')

def edit_book(request):
    if request.method == "POST":
        book_id = request.POST.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        
        book.title = request.POST.get('title')
        book.isbn = request.POST.get('isbn')
        book.quantity = request.POST.get('total_quantity')
        book.available_quantity = request.POST.get('available_quantity')
        book.thumbnail_link = request.POST.get('image_url')
        
        author_id = request.POST.get('author')
        if author_id:
            book.author = get_object_or_404(Author, id=author_id)
            
        publisher_id = request.POST.get('publisher')
        if publisher_id:
            book.publisher = get_object_or_404(Publisher, id=publisher_id)
            
        book.save()
        return redirect(reverse('admin_dashboard') + '?tab=books')
    return redirect(reverse('admin_dashboard') + '?tab=books')

def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    book_title = book.title
    book.delete()
    add_notification(f"Book '{book_title}' deleted successfully.")
    return redirect(reverse('admin_dashboard') + '?tab=books')

def fix_sequences(request):
    """Resets the database sequences to fix 'duplicate key' errors."""
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Book, Author, Publisher, Student, Circulation, Penalty])
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)
    return redirect('admin_dashboard')

def issue_book(request):
    if request.method == "POST":
        student_id = request.POST.get('student')
        book_id = request.POST.get('book')
        issue_date_str = request.POST.get('issue_date')
        
        if student_id and book_id and issue_date_str:
            student = get_object_or_404(Student, id=student_id)
            book = get_object_or_404(Book, id=book_id)
            
            issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            lib_settings = get_library_settings()
            loan_duration = lib_settings.loan_duration
            due_date = issue_date + timedelta(days=loan_duration)
            
            if book.available_quantity > 0:
                Circulation.objects.create(student=student, book=book, issue_date=issue_date, due_date=due_date, status='issued')
                book.available_quantity -= 1
                book.save()
                add_notification(f"Book '{book.title}' issued to {student.name}")
                
    return redirect(reverse('admin_dashboard') + '?tab=circulations')

def return_book(request):
    if request.method == "POST":
        circulation_id = request.POST.get('circulation_id')
        circulation = get_object_or_404(Circulation, id=circulation_id)
        
        if circulation.status == 'issued':
            book = circulation.book
            circulation.return_date = date.today()
            circulation.status = 'returned'
            
            # Calculate fine if overdue
            if circulation.return_date > circulation.due_date:
                overdue_days = (circulation.return_date - circulation.due_date).days
                
                lib_settings = get_library_settings()
                fine_amount = overdue_days * float(lib_settings.penalty_per_day)
                circulation.fine_amount = fine_amount
                
                # Create a penalty record
                Penalty.objects.create(student=circulation.student, book=circulation.book, due_date=circulation.due_date, days_overdue=overdue_days, amount=fine_amount, reason=f"Overdue: {circulation.book.title}", status='unpaid')
                add_notification(f"Book '{book.title}' returned overdue by {circulation.student.name}. Penalty: {fine_amount}")
            else:
                add_notification(f"Book '{book.title}' returned by {circulation.student.name}")
            
            circulation.save()
            
            book.available_quantity += 1
            book.save()
            
    return redirect(reverse('admin_dashboard') + '?tab=circulations')

def delete_penalty(request):
    if request.method == "POST":
        penalty_id = request.POST.get('penalty_id')
        penalty = get_object_or_404(Penalty, id=penalty_id)
        penalty.delete()
    return redirect(reverse('admin_dashboard') + '?tab=penalties')

def mark_penalty_paid(request, penalty_id):
    if request.method == "POST":
        penalty = get_object_or_404(Penalty, id=penalty_id)
        penalty.status = 'Paid'
        penalty.save()
        add_notification(f"Penalty for {penalty.student.name} marked as Paid.")
    return redirect(reverse('admin_dashboard') + '?tab=penalties')

def edit_user(request):
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        
        password = request.POST.get('password')
        if password:
            user.set_password(password)
            
        is_superuser = request.POST.get('is_superuser') == 'True'
        user.is_superuser = is_superuser
        user.is_staff = is_superuser
        
        is_active = request.POST.get('is_active') == 'True'
        user.is_active = is_active
        
        user.save()
        return redirect(reverse('admin_dashboard') + '?tab=users')
    return redirect(reverse('admin_dashboard') + '?tab=users')

def delete_user(request):
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        if user != request.user:  # Prevent deleting yourself
            user.delete()
    return redirect(reverse('admin_dashboard') + '?tab=users')

def edit_publisher(request):
    if request.method == "POST":
        publisher_id = request.POST.get('id')
        publisher = get_object_or_404(Publisher, id=publisher_id)
        publisher.name = request.POST.get('name')
        publisher.save()
    return redirect(reverse('admin_dashboard') + '?tab=publishers')

def delete_publisher(request):
    if request.method == "POST":
        publisher_id = request.POST.get('publisher_id')
        publisher = get_object_or_404(Publisher, id=publisher_id)
        publisher.delete()
    return redirect(reverse('admin_dashboard') + '?tab=publishers')

def edit_author(request):
    if request.method == "POST":
        author_id = request.POST.get('id')
        author = get_object_or_404(Author, id=author_id)
        author.name = request.POST.get('name')
        author.bio = request.POST.get('bio')
        author.save()
    return redirect(reverse('admin_dashboard') + '?tab=authors')

def delete_author(request, author_id):
    author = get_object_or_404(Author, id=author_id)
    author.delete()
    return redirect(reverse('admin_dashboard') + '?tab=authors')

def edit_student(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        student.name = request.POST.get('name')
        student.email = request.POST.get('email')
        student.phone = request.POST.get('phone')
        student.address = request.POST.get('address')
        student.save()
    return redirect(reverse('admin_dashboard') + '?tab=students')

def delete_student(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        student.delete()
    return redirect(reverse('admin_dashboard') + '?tab=students')

def update_settings(request):
    if request.method == "POST":
        settings_obj = get_library_settings()
        
        settings_obj.library_name = request.POST.get('library_name')
        settings_obj.address = request.POST.get('address')
        settings_obj.contact = request.POST.get('contact')
        settings_obj.penalty_per_day = request.POST.get('penalty_per_day')
        settings_obj.max_penalty = request.POST.get('max_penalty')
        settings_obj.loan_duration = request.POST.get('loan_duration')
        settings_obj.max_books = request.POST.get('max_books')
        settings_obj.save()
        
        add_notification("Settings updated successfully.")
    return redirect(reverse('admin_dashboard') + '?tab=settings')
