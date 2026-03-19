from django.db.models import Count
from .models import Circulation, Book

def get_recommendations_for_student(student_id, limit=3):
    # Get all books the student has borrowed
    student_history = Circulation.objects.filter(student_id=student_id).values_list('book_id', flat=True)
    
    if not student_history:
        # Cold start: Recommend the most popular books overall if no history exists
        return Book.objects.annotate(
            borrow_count=Count('circulation')
        ).filter(available_quantity__gt=0).order_by('-borrow_count')[:limit]

    # Collaborative Filtering: Find other students who borrowed the same books
    similar_students = Circulation.objects.filter(
        book_id__in=student_history
    ).exclude(student_id=student_id).values_list('student_id', flat=True)

    # Find what those similar students borrowed, that the current student HAS NOT read
    recommended_books = Book.objects.filter(
        circulation__student_id__in=similar_students,
        available_quantity__gt=0
    ).exclude(
        id__in=student_history
    ).annotate(
        match_score=Count('circulation')
    ).order_by('-match_score')[:limit]

    # Fallback to Content-based (Author) if not enough matches
    if not recommended_books.exists():
        authors_read = Book.objects.filter(id__in=student_history).values_list('author_id', flat=True)
        recommended_books = Book.objects.filter(
            author_id__in=authors_read,
            available_quantity__gt=0
        ).exclude(id__in=student_history).order_by('?')[:limit]

    return recommended_books

def get_similar_books(book_id, limit=3):
    # Find students who borrowed this specific book
    students_who_borrowed = Circulation.objects.filter(book_id=book_id).values_list('student_id', flat=True)
    
    if not students_who_borrowed:
        return Book.objects.none()

    # Recommend other books those specific students have read
    return Book.objects.filter(
        circulation__student_id__in=students_who_borrowed
    ).exclude(
        id=book_id
    ).annotate(match_score=Count('circulation')).order_by('-match_score')[:limit]