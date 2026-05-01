from .models import Contact

def unread_messages(request):
    if request.user.is_authenticated and request.user.is_staff:
        unread_count = Contact.objects.filter(is_read=False).count()
    else:
        unread_count = 0
    return {'unread_count': unread_count}