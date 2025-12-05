"""Authentication views."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.http import require_POST

from ..forms import LoginForm, RegisterForm
from ..models import UserPreferences
from .helpers import get_or_create_preferences


class LoginView(View):
    """User login view."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = LoginForm()
        return render(request, 'cards/login.html', {'form': form})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Sync theme from preferences to response
            get_or_create_preferences(user)
            response = redirect('dashboard')
            return response

        return render(request, 'cards/login.html', {'form': form})


class RegisterView(View):
    """User registration view."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = RegisterForm()
        return render(request, 'cards/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create default preferences
            UserPreferences.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect('dashboard')

        return render(request, 'cards/register.html', {'form': form})


@require_POST
def logout_view(request):
    """User logout view."""
    logout(request)
    return redirect('login')
