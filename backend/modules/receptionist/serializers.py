from rest_framework import serializers
from .models import TblAppointment, TblPatient

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = TblPatient
        fields = ["patient_id", "first_name", "last_name", "email", "contact_number"]

class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    appointment_status_name = serializers.CharField(
        source="appointment_status.appointment_status_name",
        read_only=True
    )

    class Meta:
        model = TblAppointment
        fields = [
            "appointment_id",
            "appointment_date",
            "appointment_start_time",
            "appointment_end_time",
            "appointment_status",
            "appointment_status_name",
            "patient",
        ]
