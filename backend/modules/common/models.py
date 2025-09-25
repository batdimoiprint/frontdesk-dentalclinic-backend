# modules/common/models.py
from django.db import models

class TblRoles(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50)  # match your enum max length

    class Meta:
        db_table = "tbl_roles"   # map to existing Supabase table
        managed = False          # Django won’t manage migrations


class TblLoginCredentials(models.Model):
    login_id = models.BigAutoField(primary_key=True)
    staff_id = models.BigIntegerField()
    role = models.ForeignKey(
        TblRoles,
        on_delete=models.CASCADE,
        db_column="role_id",   # maps to tbl_roles.role_id
        null=True,
        blank=True,
    )
    email = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "tbl_login_credentials"  # map to existing Supabase table
        managed = False
