from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Author, Publisher, Book, Member, Circulation, Penalty, LibrarySettings, Notification
from django.contrib import messages
from django.db import IntegrityError
from django.db import connection
from django.core.management.color import no_style
from datetime import date, datetime, timedelta
import json
from django.db.models import Sum, Count

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

def admin_dashboard(request):
    if request.method == 'POST' and 'notification_action' in request.POST:
        action = request.POST.get('notification_action')
        if action == 'clear':
            Notification.objects.all().delete()
        elif action == 'mark_read':
            Notification.objects.filter(read=False).update(read=True)
        return redirect('admin_dashboard')

    search_query = request.GET.get('search_query', '')
    books = Book.objects.all().order_by('-id')
    
    if search_query:
        books = books.filter(title__icontains=search_query)

    # Calculate statistics for dashboard
    total_members = Member.objects.count()
    issued_books_count = Circulation.objects.filter(status='issued').count()
    reserved_books_count = Book.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
    overdue_books_count = Circulation.objects.filter(status='issued', due_date__lt=date.today()).count()

    notifications = get_notifications()
    unread_count = Notification.objects.filter(read=False).count()

    # Chart Data
    chart_range = request.GET.get('chart_range', '6_months')
    chart_labels = []
    issue_counts = []
    member_counts = []
    revenue_data = []
    today = date.today()
    
    if chart_range == 'last_week':
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            chart_labels.append(d.strftime('%a'))
            issue_counts.append(Circulation.objects.filter(issue_date=d).count())
            # Using __date for joined_date in case it is DateTimeField, otherwise exact match for DateField
            member_counts.append(Member.objects.filter(joined_date__year=d.year, joined_date__month=d.month, joined_date__day=d.day).count())
            # Assuming Penalty has created_at
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
            member_counts.append(Member.objects.filter(joined_date__year=y, joined_date__month=m).count())
            monthly_revenue = Penalty.objects.filter(created_at__year=y, created_at__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
            revenue_data.append(float(monthly_revenue))
    else: # 6 months (default)
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            chart_labels.append(date(y, m, 1).strftime('%b'))
            issue_counts.append(Circulation.objects.filter(issue_date__year=y, issue_date__month=m).count())
            member_counts.append(Member.objects.filter(joined_date__year=y, joined_date__month=m).count())
            monthly_revenue = Penalty.objects.filter(created_at__year=y, created_at__month=m).aggregate(Sum('amount'))['amount__sum'] or 0
            revenue_data.append(float(monthly_revenue))

    context = {
        'books': books,
        'search_query': search_query,
        'total_books': Book.objects.count(),
        'total_members': total_members,
        'issued_books_count': issued_books_count,
        'reserved_books_count': reserved_books_count,
        'overdue_books_count': overdue_books_count,
        'authors': Author.objects.annotate(book_count=Count('book')).order_by('-book_count'),
        'publishers': Publisher.objects.all().order_by('name'),
        'members': Member.objects.all().order_by('-id'),
        'users': User.objects.all().order_by('-id'),
        'circulations': Circulation.objects.all().order_by('-issue_date', '-id'),
        'penalties': Penalty.objects.all(),
        'lib_settings': get_library_settings(),
        'notifications': notifications,
        'unread_count': unread_count,
        'chart_labels': json.dumps(chart_labels),
        'issue_counts': json.dumps(issue_counts),
        'member_counts': json.dumps(member_counts),
        'revenue_data': json.dumps(revenue_data),
    }
    return render(request, 'admin_library.html', context)

def admin_logout(request):
    logout(request)
    return redirect('admin_login')

def add_book(request):
    if request.method == "POST":
        title = request.POST.get('title')
        author_id = request.POST.get('author')
        publisher_id = request.POST.get('publisher')
        isbn = request.POST.get('isbn')
        total_qty = request.POST.get('total_quantity')
        avail_qty = request.POST.get('available_quantity')
        image_url = request.POST.get('image_url')
        
        if not author_id:
            add_notification("Failed to add book: Please select an author.")
            return redirect(reverse('admin_dashboard') + '?tab=books')

        if not publisher_id:
            add_notification("Failed to add book: Please select a publisher.")
            return redirect(reverse('admin_dashboard') + '?tab=books')
            
        if Book.objects.filter(isbn=isbn).exists():
            add_notification("Failed to add book: A book with this ISBN already exists.")
            return redirect(reverse('admin_dashboard') + '?tab=books')

        author = get_object_or_404(Author, id=author_id)
        publisher = get_object_or_404(Publisher, id=publisher_id)
        
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
                    # Fix sequence
                    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Book])
                    with connection.cursor() as cursor:
                        for sql in sequence_sql:
                            cursor.execute(sql)
                    # Retry creation
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
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_superuser = is_superuser
            user.is_staff = is_superuser # Admins are usually staff
            user.save()
        return redirect('admin_dashboard')

def add_penalty(request):
    if request.method == "POST":
        member_input = request.POST.get('member')
        username_input = request.POST.get('username')
        amount = request.POST.get('amount')
        reason = request.POST.get('reason')
        book_title = request.POST.get('book_title')
        
        member = None
        if member_input and member_input.isdigit():
            member = Member.objects.filter(id=member_input).first()
            
        if not member and member_input:
            member = Member.objects.filter(name__iexact=member_input).first()
            
        if not member and username_input:
            member = Member.objects.filter(name__iexact=username_input).first()

        book = None
        if book_title:
            book = Book.objects.filter(title__iexact=book_title).first()

        if not reason and book_title:
            reason = f"Book: {book_title}"

        if member and amount:
            Penalty.objects.create(member=member, book=book, amount=amount, reason=reason or "Penalty")
        return redirect('admin_dashboard')

def add_member(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        Member.objects.create(name=name, email=email, phone=phone, address=address)
        return redirect('admin_dashboard')

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
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Book, Author, Publisher, Member, Circulation, Penalty])
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)
    return redirect('admin_dashboard')

def issue_book(request):
    if request.method == "POST":
        member_id = request.POST.get('member')
        book_id = request.POST.get('book')
        issue_date_str = request.POST.get('issue_date')
        
        if member_id and book_id and issue_date_str:
            member = get_object_or_404(Member, id=member_id)
            book = get_object_or_404(Book, id=book_id)
            
            issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            lib_settings = get_library_settings()
            loan_duration = lib_settings.loan_duration
            due_date = issue_date + timedelta(days=loan_duration)
            
            if book.available_quantity > 0:
                Circulation.objects.create(member=member, book=book, issue_date=issue_date, due_date=due_date, status='issued')
                book.available_quantity -= 1
                book.save()
                add_notification(f"Book '{book.title}' issued to {member.name}")
                
    return redirect(reverse('admin_dashboard') + '?tab=circulations')

def return_book(request):
    if request.method == "POST":
        circulation_id = request.POST.get('circulation_id')
        circulation = get_object_or_404(Circulation, id=circulation_id)
        
        if circulation.status == 'issued':
            circulation.return_date = date.today()
            circulation.status = 'returned'
            
            # Calculate fine if overdue
            if circulation.return_date > circulation.due_date:
                overdue_days = (circulation.return_date - circulation.due_date).days
                
                lib_settings = get_library_settings()
                fine_amount = overdue_days * float(lib_settings.penalty_per_day)
                circulation.fine_amount = fine_amount
                
                # Create a penalty record
                Penalty.objects.create(member=circulation.member, book=circulation.book, due_date=circulation.due_date, days_overdue=overdue_days, amount=fine_amount, reason=f"Overdue: {circulation.book.title}", status='unpaid')
                add_notification(f"Book '{book.title}' returned overdue by {circulation.member.name}. Penalty: {fine_amount}")
            else:
                add_notification(f"Book '{book.title}' returned by {circulation.member.name}")
            
            circulation.save()
            
            book = circulation.book
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
        add_notification(f"Penalty for {penalty.member.name} marked as Paid.")
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

def edit_member(request):
    if request.method == "POST":
        member_id = request.POST.get('member_id')
        member = get_object_or_404(Member, id=member_id)
        member.name = request.POST.get('name')
        member.email = request.POST.get('email')
        member.phone = request.POST.get('phone')
        member.address = request.POST.get('address')
        member.save()
    return redirect(reverse('admin_dashboard') + '?tab=members')

def delete_member(request):
    if request.method == "POST":
        member_id = request.POST.get('member_id')
        member = get_object_or_404(Member, id=member_id)
        member.delete()
    return redirect(reverse('admin_dashboard') + '?tab=members')

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
