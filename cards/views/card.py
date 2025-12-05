"""Card CRUD views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from ..models import Deck, Card
from ..forms import CardForm


class CardCreateView(LoginRequiredMixin, CreateView):
    """Create a new card."""
    model = Card
    form_class = CardForm
    template_name = 'cards/card_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['deck'] = get_object_or_404(Deck, pk=self.kwargs['deck_pk'], owner=self.request.user)
        return context

    def form_valid(self, form):
        deck = get_object_or_404(Deck, pk=self.kwargs['deck_pk'], owner=self.request.user)
        form.instance.deck = deck
        messages.success(self.request, 'Card created!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('deck_detail', kwargs={'pk': self.kwargs['deck_pk']})


class CardUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing card."""
    model = Card
    form_class = CardForm
    template_name = 'cards/card_form.html'

    def get_queryset(self):
        return Card.objects.filter(deck__owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['deck'] = self.object.deck
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Card updated!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('deck_detail', kwargs={'pk': self.object.deck.pk})


class CardDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a card."""
    model = Card
    template_name = 'cards/card_confirm_delete.html'

    def get_queryset(self):
        return Card.objects.filter(deck__owner=self.request.user)

    def get_success_url(self):
        return reverse_lazy('deck_detail', kwargs={'pk': self.object.deck.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Card deleted.')
        return super().form_valid(form)
