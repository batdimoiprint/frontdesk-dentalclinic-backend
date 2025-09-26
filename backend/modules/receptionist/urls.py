from django.urls import path
from .views import (
    PendingAppointmentsView,
    ApproveAppointmentView,
    CancelAppointmentView,
    BillAppointmentView,
    AppointmentListView,
)

urlpatterns = [
    # List all pending appointments
    path("appointments/pending/", PendingAppointmentsView.as_view(), name="pending-appointments"),

    # Approve, Cancel, Bill actions
    path("appointments/<int:pk>/approve/", ApproveAppointmentView.as_view(), name="approve-appointment"),
    path("appointments/<int:pk>/cancel/", CancelAppointmentView.as_view(), name="cancel-appointment"),
    path("appointments/<int:pk>/bill/", BillAppointmentView.as_view(), name="bill-appointment"),

    # General list with filters (?status=Approved&date=2025-09-27&patient=Doe)
    path("appointments/", AppointmentListView.as_view(), name="all-appointments"),
]
