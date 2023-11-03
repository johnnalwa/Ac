from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# Register your models here.
from .models import *

admin.site.register(Client)
admin.site.register(Attendance)
admin.site.register(Sale)
admin.site.register(Commission)
admin.site.register(RoutePlan)