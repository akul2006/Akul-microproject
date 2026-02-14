from django.contrib import admin
from .models import Author, Publisher, Book, Member, Circulation, BookRequest, Penalty

admin.site.register(Author)
admin.site.register(Publisher)
admin.site.register(Book)
admin.site.register(Member)
admin.site.register(Circulation)
admin.site.register(BookRequest)
admin.site.register(Penalty)