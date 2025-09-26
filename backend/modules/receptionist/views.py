from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import TblAppointment, TblAppointmentStatus
from .serializers import AppointmentSerializer


# ✅ GET /appointments/pending/
class PendingAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return TblAppointment.objects.filter(
            appointment_status__appointment_status_name="Pending"
        )


# ✅ PUT /appointments/{id}/approve/
class ApproveAppointmentView(APIView):
    def put(self, request, pk):
        appointment = get_object_or_404(TblAppointment, pk=pk)
        approved_status = get_object_or_404(
            TblAppointmentStatus, appointment_status_name="Approved"
        )
        appointment.appointment_status = approved_status
        appointment.remarks = request.data.get("remarks", "")
        appointment.save()
        return Response(
            {"message": "Appointment marked as Approved"},
            status=status.HTTP_200_OK,
        )


# ✅ PUT /appointments/{id}/cancel/
class CancelAppointmentView(APIView):
    def put(self, request, pk):
        appointment = get_object_or_404(TblAppointment, pk=pk)
        cancelled_status = get_object_or_404(
            TblAppointmentStatus, appointment_status_name="Cancelled"
        )
        appointment.appointment_status = cancelled_status
        appointment.remarks = request.data.get(
            "remarks", "Appointment cancelled by receptionist"
        )
        appointment.save()
        return Response(
            {"message": "Appointment marked as Cancelled"},
            status=status.HTTP_200_OK,
        )


# ✅ PUT /appointments/{id}/bill/
class BillAppointmentView(APIView):
    def put(self, request, pk):
        appointment = get_object_or_404(TblAppointment, pk=pk)
        billed_status = get_object_or_404(
            TblAppointmentStatus, appointment_status_name="Billed"
        )
        appointment.appointment_status = billed_status
        appointment.remarks = request.data.get("remarks", "Marked as billed")
        appointment.save()
        return Response(
            {"message": "Appointment marked as Billed"},
            status=status.HTTP_200_OK,
        )


# ✅ GET /appointments/?status=Approved&date=2025-09-27&patient=Doe
class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        queryset = TblAppointment.objects.all()

        # query parameters
        status_param = self.request.query_params.get("status")
        date_param = self.request.query_params.get("date")
        patient_param = self.request.query_params.get("patient")

        if status_param:
            # Only allow filtering by valid statuses
            valid_statuses = ["Approved", "Cancelled", "Billed", "Pending"]
            if status_param in valid_statuses:
                queryset = queryset.filter(
                    appointment_status__appointment_status_name=status_param
                )
        if date_param:
            queryset = queryset.filter(appointment_date=date_param)
        if patient_param:
            queryset = queryset.filter(patient__last_name__icontains=patient_param)

        return queryset
