"""Landing page view."""

from django.shortcuts import render, redirect


def landing(request):
    """Marketing landing page for unauthenticated users."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'cards/landing.html')
