"""Deck CRUD views."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from ..models import Deck, Card
from ..forms import DeckForm


class DeckListView(LoginRequiredMixin, ListView):
    """List all decks for the current user."""
    model = Deck
    template_name = 'cards/deck_list.html'
    context_object_name = 'decks'

    def get_queryset(self):
        now = timezone.now()
        return Deck.objects.filter(owner=self.request.user).annotate(
            card_count=Count('cards'),
            due_count=Count('cards', filter=Q(cards__next_review__lte=now))
        )


class DeckCreateView(LoginRequiredMixin, CreateView):
    """Create a new deck."""
    model = Deck
    form_class = DeckForm
    template_name = 'cards/deck_form.html'
    success_url = reverse_lazy('deck_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, f'Deck "{form.instance.name}" created!')
        return super().form_valid(form)


class DeckUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing deck."""
    model = Deck
    form_class = DeckForm
    template_name = 'cards/deck_form.html'
    success_url = reverse_lazy('deck_list')

    def get_queryset(self):
        return Deck.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f'Deck "{form.instance.name}" updated!')
        return super().form_valid(form)


class DeckDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a deck."""
    model = Deck
    template_name = 'cards/deck_confirm_delete.html'
    success_url = reverse_lazy('deck_list')

    def get_queryset(self):
        return Deck.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f'Deck "{self.object.name}" deleted.')
        return super().form_valid(form)


@login_required
def deck_detail(request, pk):
    """View deck details and cards."""
    deck = get_object_or_404(Deck, pk=pk, owner=request.user)
    cards = deck.cards.all()
    now = timezone.now()
    due_count = cards.filter(next_review__lte=now).count()

    context = {
        'deck': deck,
        'cards': cards,
        'due_count': due_count,
    }
    return render(request, 'cards/deck_detail.html', context)


@login_required
def deck_export(request, pk):
    """Export a deck as JSON file."""
    deck = get_object_or_404(Deck, pk=pk, owner=request.user)

    export_data = {
        'name': deck.name,
        'description': deck.description,
        'exported_at': timezone.now().isoformat(),
        'cards': [
            {
                'card_type': card.card_type,
                'front': card.front,
                'back': card.back,
                'notes': card.notes,
            }
            for card in deck.cards.all()
        ]
    }

    response = HttpResponse(
        json.dumps(export_data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    # Sanitize filename
    safe_name = "".join(c for c in deck.name if c.isalnum() or c in (' ', '-', '_')).strip()
    response['Content-Disposition'] = f'attachment; filename="{safe_name}.json"'
    return response


@login_required
def deck_import(request):
    """Import a deck from JSON file."""
    if request.method == 'POST':
        uploaded_file = request.FILES.get('deck_file')

        if not uploaded_file:
            messages.error(request, 'Please select a file to import.')
            return redirect('deck_list')

        if not uploaded_file.name.endswith('.json'):
            messages.error(request, 'Please upload a JSON file.')
            return redirect('deck_list')

        try:
            content = uploaded_file.read().decode('utf-8')
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            messages.error(request, f'Invalid JSON file: {e}')
            return redirect('deck_list')

        # Validate required fields
        if 'name' not in data:
            messages.error(request, 'Invalid deck file: missing "name" field.')
            return redirect('deck_list')

        if 'cards' not in data or not isinstance(data['cards'], list):
            messages.error(request, 'Invalid deck file: missing or invalid "cards" field.')
            return redirect('deck_list')

        # Check for duplicate deck name
        deck_name = data['name']
        if Deck.objects.filter(name=deck_name, owner=request.user).exists():
            # Append number to make unique
            counter = 1
            while Deck.objects.filter(name=f"{deck_name} ({counter})", owner=request.user).exists():
                counter += 1
            deck_name = f"{deck_name} ({counter})"

        # Create deck
        deck = Deck.objects.create(
            name=deck_name,
            description=data.get('description', ''),
            owner=request.user
        )

        # Create cards
        valid_card_types = [choice[0] for choice in Card.CardType.choices]
        cards_created = 0

        for card_data in data['cards']:
            if 'front' not in card_data:
                continue  # Skip invalid cards

            card_type = card_data.get('card_type', 'basic')
            if card_type not in valid_card_types:
                card_type = 'basic'

            Card.objects.create(
                deck=deck,
                card_type=card_type,
                front=card_data['front'],
                back=card_data.get('back', ''),
                notes=card_data.get('notes', '')
            )
            cards_created += 1

        messages.success(request, f'Imported deck "{deck_name}" with {cards_created} cards!')
        return redirect('deck_detail', pk=deck.pk)

    # GET request - show import form
    return render(request, 'cards/deck_import.html')


@login_required
@require_POST
def deck_reset(request, pk):
    """Reset all cards in a deck to their initial state."""
    deck = get_object_or_404(Deck, pk=pk, owner=request.user)

    # Verify deck name matches for confirmation
    confirm_name = request.POST.get('confirm_name', '').strip()
    if confirm_name != deck.name:
        return JsonResponse({
            'success': False,
            'error': 'Deck name does not match'
        }, status=400)

    # Reset all cards in the deck
    card_count = deck.cards.update(
        ease_factor=2.5,
        interval=0,
        repetitions=0,
        next_review=timezone.now(),
        last_reviewed=None
    )

    # Delete all review logs for cards in this deck
    from ..models import ReviewLog
    ReviewLog.objects.filter(card__deck=deck).delete()

    return JsonResponse({
        'success': True,
        'message': f'Reset {card_count} cards in "{deck.name}"',
        'card_count': card_count
    })
