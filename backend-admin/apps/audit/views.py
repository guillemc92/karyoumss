"""
Vista de auditoría: lista las LogEntry (django-auditlog) del bounded context admin.

Append-Only por construcción (django-auditlog no expone DELETE en LogEntry).
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminRole


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminRole])
def audit_log_view(request):
    """
    GET /api/admin/audit/logs
    Query params: ?limit=50&offset=0&action=create&model=adminuser
    """
    from auditlog.models import LogEntry

    limit = int(request.query_params.get('limit', 50))
    offset = int(request.query_params.get('offset', 0))
    action_flag = request.query_params.get('action')  # 'create' | 'update' | 'delete'
    model_name = request.query_params.get('model')

    qs = LogEntry.objects.filter(content_type__app_label__in=['users', 'audit'])
    if action_flag:
        flag_map = {'create': 0, 'update': 1, 'delete': 2}
        if action_flag in flag_map:
            qs = qs.filter(action=flag_map[action_flag])
    if model_name:
        qs = qs.filter(content_type__model=model_name)

    total = qs.count()
    entries = qs.order_by('-timestamp')[offset:offset + limit]

    data = {
        'total': total,
        'limit': limit,
        'offset': offset,
        'results': [
            {
                'timestamp': e.timestamp.isoformat(),
                'action': {0: 'create', 1: 'update', 2: 'delete'}.get(e.action, 'unknown'),
                'actor': e.actor.username if e.actor else None,
                'object_pk': e.object_pk,
                'model': e.content_type.model,
                'changes': e.changes or {},
            }
            for e in entries
        ],
    }
    return Response(data)