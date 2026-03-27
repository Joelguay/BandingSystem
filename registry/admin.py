from django.contrib import admin
from .models import Breeder, Chicken, OwnershipHistory, AuditLog


# Register your models here.
admin.site.register(Breeder)
admin.site.register(Chicken)
admin.site.register(OwnershipHistory)
admin.site.register(AuditLog)


