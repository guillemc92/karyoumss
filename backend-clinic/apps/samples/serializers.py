from rest_framework import serializers

from .models import Sample


class SampleListItemSerializer(serializers.ModelSerializer):
    analyst_name = serializers.CharField(source='analyst.get_full_name', default='', read_only=True)
    has_karyotype = serializers.SerializerMethodField()

    class Meta:
        model = Sample
        fields = [
            'id', 'chn_code', 'patient_ref', 'status',
            'analyst_name', 'has_karyotype', 'created_at', 'updated_at',
        ]

    def get_has_karyotype(self, obj):
        return obj.status in ('READY', 'VALIDATED')


class SampleReadSerializer(serializers.ModelSerializer):
    analyst_name = serializers.CharField(source='analyst.get_full_name', default='', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.get_full_name', default='', read_only=True)

    class Meta:
        model = Sample
        fields = [
            'id', 'chn_code', 'patient_ref', 'image_path', 'status',
            'analyst', 'analyst_name', 'supervisor', 'supervisor_name',
            'metadata', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'analyst', 'supervisor', 'created_at', 'updated_at']


class SampleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        fields = ['chn_code', 'patient_ref', 'image_path', 'metadata']

    def validate_chn_code(self, value):
        if Sample.objects.filter(chn_code=value, is_active=True).exists():
            raise serializers.ValidationError('CHN ya existe (CHN_DUPLICATE)')
        return value


class SampleUpdateSerializer(serializers.ModelSerializer):
    """PATCH parcial. RN-04: solo patient_ref y metadata son editables.

    status, chn_code, image_path, iscn_nomenclature NO se aceptan aquí.
    """

    class Meta:
        model = Sample
        fields = ['patient_ref', 'metadata']

    def validate(self, attrs):
        forbidden = set(self.initial_data.keys()) & {
            'status', 'chn_code', 'image_path', 'iscn_nomenclature', 'edits',
        }
        if forbidden:
            raise serializers.ValidationError(
                {f: 'FIELD_NOT_ALLOWED' for f in forbidden}
            )
        return attrs
