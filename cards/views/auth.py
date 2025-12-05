"""Authentication views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.decorators.http import require_POST

from ..forms import LoginForm, RegisterForm
from ..models import UserPreferences, EmailVerificationToken
from .helpers import get_or_create_preferences


def send_verification_email(user, token, request):
    """Send email verification link to user."""
    verification_url = request.build_absolute_uri(f'/verify-email/{token.token}/')
    subject = 'Verify your email address'
    message = f"""Hi {user.username},

Thanks for creating an account! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account, you can safely ignore this email.
"""
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


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
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            # Create default preferences
            UserPreferences.objects.create(user=user)
            # Create verification token and send email
            token = EmailVerificationToken.create_for_user(user)
            send_verification_email(user, token, request)
            return redirect('verification_sent')

        return render(request, 'cards/register.html', {'form': form})


@require_POST
def logout_view(request):
    """User logout view."""
    logout(request)
    return redirect('login')


def verification_sent(request):
    """Show page confirming verification email was sent."""
    return render(request, 'cards/verification_sent.html')


def verify_email(request, token):
    """Verify user's email address using token."""
    verification = get_object_or_404(EmailVerificationToken, token=token)

    if verification.is_expired():
        return render(request, 'cards/verification_expired.html', {
            'user': verification.user
        })

    user = verification.user
    user.is_active = True
    user.save()
    verification.delete()

    messages.success(request, 'Your email has been verified. You can now log in.')
    return redirect('login')


class ResendVerificationView(View):
    """Resend verification email to user."""

    def get(self, request):
        return render(request, 'cards/resend_verification.html')

    def post(self, request):
        from django.contrib.auth.models import User

        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'cards/resend_verification.html')

        try:
            user = User.objects.get(email=email, is_active=False)
            token = EmailVerificationToken.create_for_user(user)
            send_verification_email(user, token, request)
            messages.success(request, 'Verification email sent. Please check your inbox.')
        except User.DoesNotExist:
            # Don't reveal whether email exists - just show success message
            messages.success(request, 'If an unverified account exists with this email, a verification link has been sent.')

        return redirect('verification_sent')
