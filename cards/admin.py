from django.contrib import admin
from .models import Deck, Card, ReviewLog, ReviewReminder, UserPreferences


class CardInline(admin.TabularInline):
    model = Card
    extra = 1
    fields = ['card_type', 'front', 'back', 'next_review']
    readonly_fields = ['next_review']


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'card_count', 'cards_due_count', 'created_at']
    list_filter = ['owner', 'created_at']
    search_fields = ['name', 'description']
    inlines = [CardInline]

    def card_count(self, obj):
        return obj.cards.count()
    card_count.short_description = 'Cards'


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['front_preview', 'deck', 'card_type', 'next_review', 'ease_factor', 'repetitions']
    list_filter = ['deck', 'card_type', 'next_review']
    search_fields = ['front', 'back']
    readonly_fields = ['ease_factor', 'interval', 'repetitions', 'next_review', 'last_reviewed']

    def front_preview(self, obj):
        return obj.front[:50] + '...' if len(obj.front) > 50 else obj.front
    front_preview.short_description = 'Front'


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ['card', 'quality', 'interval_before', 'interval_after', 'reviewed_at']
    list_filter = ['quality', 'reviewed_at']
    readonly_fields = ['card', 'quality', 'ease_factor_before', 'ease_factor_after',
                       'interval_before', 'interval_after', 'reviewed_at']


@admin.register(ReviewReminder)
class ReviewReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'enabled', 'frequency', 'preferred_time', 'last_sent']
    list_filter = ['enabled', 'frequency']


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'cards_per_session', 'updated_at']
    list_filter = ['theme']
