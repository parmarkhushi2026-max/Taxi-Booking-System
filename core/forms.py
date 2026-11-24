from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import CustomAdmin, User as AppUser


class AdminLoginForm(AuthenticationForm):
    """
    Standard Django AuthenticationForm customized for Admin Login.
    Restricts login strictly to staff and superusers.
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


class AdminRegistrationForm(forms.ModelForm):
    """
    Manual Admin Registration Form.
    Stores data in the custom admin table (custom_admin_users).
    """
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'e.g. Vikramaditya Rathore',
            'id': 'fullName',
            'autofocus': True,
        })
    )
    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'e.g. admin_vikram',
            'id': 'adminUsername',
            'autocomplete': 'username',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'admin@taxibooking.com',
            'id': 'adminEmail',
            'autocomplete': 'email',
        })
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': '+91 98765 43210',
            'id': 'adminPhone',
        })
    )
    role = forms.ChoiceField(
        choices=CustomAdmin.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-control-custom w-100',
            'id': 'adminRole',
        })
    )
    profile_image = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'id': 'adminProfileImage',
            'accept': 'image/*',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Create strong admin password',
            'id': 'regPassword',
            'autocomplete': 'new-password',
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Confirm admin password',
            'id': 'confirmPassword',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = CustomAdmin
        fields = ['full_name', 'username', 'email', 'phone', 'role', 'profile_image', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if CustomAdmin.objects.filter(username__iexact=username).exists():
            raise ValidationError("This admin username is already registered in the custom admin table.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomAdmin.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match. Please verify both entries.")
            if len(password) < 6:
                raise ValidationError("Password must be at least 6 characters long.")
        return cleaned_data


class AdminForgotPasswordForm(forms.Form):
    """
    Forgot Password Form for Admin Accounts.
    Accepts the registered email address.
    """
    email = forms.EmailField(
        label="Registered Admin Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'e.g. admin@taxibooking.com',
            'id': 'forgotEmail',
            'autofocus': True,
            'autocomplete': 'email',
        })
    )


class VerifyOTPForm(forms.Form):
    """
    OTP Verification Form for Password Reset.
    Validates the 6-digit numeric OTP generated via Python random.
    """
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        label="6-Digit OTP Code",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100 text-center fs-3 fw-bold',
            'placeholder': '• • • • • •',
            'id': 'otpInput',
            'maxlength': '6',
            'autofocus': True,
            'autocomplete': 'one-time-code',
            'style': 'letter-spacing: 8px;',
        })
    )


class AdminResetPasswordForm(forms.Form):
    """
    Form to allow resetting admin password after OTP verification.
    """
    new_password = forms.CharField(
        label="New Password",
        min_length=6,
        error_messages={'min_length': 'Password must be at least 6 characters long.'},
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Enter new password (min. 6 characters)',
            'id': 'newPassword',
            'autofocus': True,
            'autocomplete': 'new-password',
        })
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        min_length=6,
        error_messages={'min_length': 'Password must be at least 6 characters long.'},
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Re-enter new password to confirm',
            'id': 'confirmPassword',
            'autocomplete': 'new-password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError("Passwords do not match. Please verify both entries.")
            if len(new_password) < 6:
                raise ValidationError("Password must be at least 6 characters long.")
        return cleaned_data


class AppUserCreateForm(forms.ModelForm):
    """
    Form for Administrator to manually create a new App User / Rider.
    """
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Full Name (e.g. Ramesh Kumar)',
            'id': 'userName',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'user@example.com',
            'id': 'userEmail',
        })
    )
    mobile = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': '+91 98765 43210',
            'id': 'userMobile',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Enter initial password',
            'id': 'userPassword',
        })
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'userIsActive',
        })
    )

    class Meta:
        model = AppUser
        fields = ['name', 'email', 'mobile', 'password', 'is_active']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if AppUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        if AppUser.objects.filter(mobile=mobile).exists():
            raise ValidationError("A user with this mobile number already exists.")
        return mobile

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class AppUserEditForm(forms.ModelForm):
    """
    Form for Administrator to edit an existing App User / Rider.
    Allows updating name, email, mobile, is_active status, and optional new password.
    """
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Full Name',
            'id': 'editUserName',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'user@example.com',
            'id': 'editUserEmail',
        })
    )
    mobile = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': '+91 98765 43210',
            'id': 'editUserMobile',
        })
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-custom w-100',
            'placeholder': 'Leave blank to keep existing password',
            'id': 'editUserPassword',
        }),
        help_text="Leave blank if you do not want to change the user's password."
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'editUserIsActive',
        })
    )

    class Meta:
        model = AppUser
        fields = ['name', 'email', 'mobile', 'is_active']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        query = AppUser.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        query = AppUser.objects.filter(mobile=mobile)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise ValidationError("A user with this mobile number already exists.")
        return mobile

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user


