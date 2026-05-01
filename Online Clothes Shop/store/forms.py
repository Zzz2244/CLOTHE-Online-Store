from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductVariant
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image']

VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    fields=('size', 'stock'),
    extra=0,
    can_delete=False
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user