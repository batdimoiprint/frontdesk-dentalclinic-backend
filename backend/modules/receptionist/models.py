from django.db import models


class TblPatient(models.Model):
    patient_id = models.BigAutoField(primary_key=True)
    last_name = models.CharField(max_length=255)  # NOT NULL in schema
    first_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    contact_number = models.CharField(max_length=255, null=True, blank=True)
    patient_image_url = models.CharField(
        db_column="Patient_image_url",  # ✅ exact column name in DB
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "tbl_patient"


class TblAppointmentStatus(models.Model):
    appointment_status_id = models.BigAutoField(primary_key=True)
    appointment_status_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "tbl_appointment_status"


class TblAppointment(models.Model):
    appointment_id = models.BigAutoField(primary_key=True)
    patient = models.ForeignKey(TblPatient, models.DO_NOTHING, db_column="patient_id")
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    appointment_status = models.ForeignKey(
        TblAppointmentStatus,
        models.DO_NOTHING,
        db_column="appointment_status_id",
        null=True,
        blank=True,
    )
    appointment_date = models.DateField(null=True, blank=True)
    appointment_start_time = models.TimeField(null=True, blank=True)
    appointment_end_time = models.TimeField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=50,  # USER-DEFINED in schema, treat as text
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "tbl_appointment"
