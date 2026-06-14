from django.conf import settings
from django.db import models


class AccessLog(models.Model):
    RESULT_SUCCESS = 'success'
    RESULT_FAILURE = 'failure'
    RESULT_DENIED = 'denied'
    RESULT_LOCKED = 'locked'
    RESULT_CHOICES = [
        (RESULT_SUCCESS, 'Success'),
        (RESULT_FAILURE, 'Failure'),
        (RESULT_DENIED, 'Denied'),
        (RESULT_LOCKED, 'Locked'),
    ]

    # Nullable FK — keep logs even if user is deleted
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='access_logs',
        db_index=True,
    )
    user_email = models.EmailField(blank=True, db_index=True)  # Snapshot, survives user deletion
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    http_method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=512, blank=True, db_index=True)
    action = models.CharField(max_length=100, db_index=True)   # e.g. 'login', 'users.create'
    resource = models.CharField(max_length=255, blank=True)    # e.g. 'user:42', 'role:3'
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, db_index=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        db_table = 'audit_access_log'
        ordering = ['-timestamp']
        verbose_name = 'Access Log'
        verbose_name_plural = 'Access Logs'
        indexes = [
            models.Index(fields=['timestamp', 'result']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['action', 'result']),
        ]

    def __str__(self):
        return f'{self.timestamp} | {self.user_email} | {self.action} | {self.result}'
