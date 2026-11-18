from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class AdminLoginForm(AuthenticationForm):
    """
    Standard Django AuthenticationForm customized for Admin Login.
    Restricts login strictly to staff and superusers (No registration).
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Enter admin username',
            'id': 'username',
            'autofocus': True,
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Enter admin password',
            'id': 'password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'rememberMe',
        })
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff or user.is_superuser):
            raise ValidationError(
                "Access denied: This portal is strictly for authorized administrators.",
                code='not_admin',
            )
