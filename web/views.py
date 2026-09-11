from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from subscriptions.models import Subscription

from .forms import SignupForm, SubscriptionForm


def home(request):
    if request.user.is_authenticated:
        return redirect("web:dashboard")
    return render(request, "web/home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. Add your first subscription below.")
            return redirect("web:dashboard")
    else:
        form = SignupForm()

    return render(request, "web/signup.html", {"form": form})


@login_required
def dashboard(request):
    subscriptions = Subscription.objects.filter(user=request.user).select_related("city")
    return render(request, "web/dashboard.html", {"subscriptions": subscriptions})


@login_required
def subscription_create(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f"Subscribed to {subscription.city}.")
            return redirect("web:dashboard")
    else:
        form = SubscriptionForm()

    return render(request, "web/subscription_form.html", {"form": form, "is_edit": False})


@login_required
def subscription_edit(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)

    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription updated.")
            return redirect("web:dashboard")
    else:
        form = SubscriptionForm(instance=subscription)

    return render(
        request,
        "web/subscription_form.html",
        {"form": form, "is_edit": True, "subscription": subscription},
    )


@login_required
def subscription_delete(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)

    if request.method == "POST":
        city = subscription.city
        subscription.delete()
        messages.success(request, f"Unsubscribed from {city}.")

    return redirect("web:dashboard")
