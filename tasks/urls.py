from django.urls import path
from .views import (
    ServiceListView, ServiceRequestCreateView, RepAssignedTasksView,
    RepConfirmTaskView, RepUndoConfirmTaskView, RepDismissTaskView,
)

urlpatterns = [
    path("services/", ServiceListView.as_view()),
    path("service-requests/", ServiceRequestCreateView.as_view()),
    path("rep/tasks/", RepAssignedTasksView.as_view()),
    path("rep/tasks/<int:pk>/confirm/", RepConfirmTaskView.as_view()),
    path("rep/tasks/<int:pk>/undo-confirm/", RepUndoConfirmTaskView.as_view()),
    path("rep/tasks/<int:pk>/dismiss/", RepDismissTaskView.as_view()),
]