from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Wir verwenden das Member-Modell als Profilerweiterung (Profile) für den Standard-User.
 class Member(models.Model):
  # related_name="profile" erlaubt den Zugriff via user.profile
  # user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
  user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
  # user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
  # Felder wie firstname, lastname, joined_date werden vom User-Modell übernommen.
  # CharField ist besser für Telefonnummern als IntegerField.
  phone = models.CharField(max_length=50, null=True, blank=True)

  def __str__(self):
    # Zeigt den vollen Namen an, falls verfügbar, sonst den Benutzernamen
    return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_member(sender, instance, created, **kwargs):
    if created:
        Member.objects.create(user=instance)
