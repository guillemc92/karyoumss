import re

from rest_framework import serializers

from .models import AuditEvent, Chromosome, Karyotype, Sample, SampleType

CHN_FORMAT_RE = re.compile(r'^CHN-\d{4}-\d{2}-\d{2}-\d{4}$')

VALID_ANALYSIS_REQUESTS = {
    'karyotype_high_res', 'mosaicism', 'fish', 'array_cgh', 'fragility_study', 'other',
}


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


# ============================================================================
# Registro de Muestras (ADR-0016, SPEC-009) — endpoint compuesto
# ============================================================================


class PatientDataSerializer(serializers.Serializer):
    """Sub-objeto `patient` del registro. Nunca se persiste directo — el
    service lo escribe cifrado en PatientVault (RN-03, ADR-0016 D2)."""

    full_name = serializers.CharField(required=False, allow_blank=True, default='')
    birth_date = serializers.CharField(required=False, allow_blank=True, default='')
    document_id = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(required=False, allow_blank=True, default='')


class SampleDataSerializer(serializers.Serializer):
    """Sub-objeto `sample` del registro (campos no-PII, ADR-0016 D5)."""

    chn_code = serializers.CharField()
    sample_type = serializers.ChoiceField(choices=SampleType.choices, required=False, allow_blank=True, default='')
    culture_method = serializers.CharField(required=False, allow_blank=True, default='')
    collection_date = serializers.DateField(required=False, allow_null=True, default=None)
    reception_date = serializers.DateField(required=False, allow_null=True, default=None)
    requesting_doctor = serializers.CharField(required=False, allow_blank=True, default='')
    department = serializers.CharField(required=False, allow_blank=True, default='')
    gender = serializers.ChoiceField(choices=[('M', 'M'), ('F', 'F'), ('O', 'O')], required=False, allow_blank=True, default='')

    def validate_chn_code(self, value):
        if not CHN_FORMAT_RE.match(value):
            raise serializers.ValidationError('INVALID_CHN_FORMAT')
        return value


class ClinicalHistorySerializer(serializers.Serializer):
    """Sub-objeto `clinical_history`. Cifrado en PatientVault (RN-03)."""

    indication = serializers.CharField(required=False, allow_blank=True, default='')
    family_history = serializers.CharField(required=False, allow_blank=True, default='')


class SampleImageInputSerializer(serializers.Serializer):
    """Una imagen del array `images` del registro."""

    data_base64 = serializers.CharField()
    source = serializers.ChoiceField(choices=[('camera', 'camera'), ('upload', 'upload')])


class SampleRegisterSerializer(serializers.Serializer):
    """Serializer compuesto del endpoint POST /samples/register/ (SPEC-009 §5).

    Validación condicional draft/no-draft replica el gate real del HTML
    (submitBtn handler): draft solo exige chn_code; no-draft exige además
    patient.full_name e >=3 imágenes.
    """

    patient = PatientDataSerializer()
    sample = SampleDataSerializer()
    clinical_history = ClinicalHistorySerializer(required=False)
    analysis_requests = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    images = SampleImageInputSerializer(many=True, required=False, default=list)
    is_draft = serializers.BooleanField(default=False)

    def validate_analysis_requests(self, value):
        invalid = set(value) - VALID_ANALYSIS_REQUESTS
        if invalid:
            raise serializers.ValidationError(f'Valores no reconocidos: {sorted(invalid)}')
        return value

    def validate(self, attrs):
        if attrs.get('is_draft'):
            return attrs
        if not attrs['patient'].get('full_name'):
            raise serializers.ValidationError({'patient': {'full_name': 'PATIENT_NAME_REQUIRED'}})
        if len(attrs.get('images', [])) < 3:
            raise serializers.ValidationError({'images': 'INSUFFICIENT_IMAGES'})
        return attrs


# ============================================================================
# Cariotipo (ADR-0021, DD-KARYO-001) — P1: lectura read-only + semaforización
# ============================================================================


class ChromosomeSerializer(serializers.ModelSerializer):
    """Un cromosoma con su semáforo DERIVADO (RN-02, no persistido)."""

    semaphore = serializers.CharField(read_only=True)

    class Meta:
        model = Chromosome
        fields = [
            'id', 'predicted_class', 'position_index', 'confidence_score',
            'semaphore', 'resolution_status', 'xai_viewed', 'is_anomaly',
            'is_active', 'measures', 'bbox', 'order',
        ]


class KaryotypeSerializer(serializers.ModelSerializer):
    """Cariotipo completo + `summary` derivado (conteos + is_blocked).

    `summary` no persiste: se computa por-request desde los cromosomas.
    `is_blocked` en P1 es informativo (el bloqueo real de emisión es P2).
    """

    sample_id = serializers.UUIDField(read_only=True)
    chromosomes = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Karyotype
        fields = ['id', 'sample_id', 'model_version', 'generated_at', 'summary', 'chromosomes']

    def _active_chromosomes(self, obj):
        # P3: los fragmentos absorbidos por JOIN quedan is_active=False y no
        # deben aparecer en el visor ni contar en el summary (DD-KARYO-003).
        return [c for c in obj.chromosomes.all() if c.is_active]

    def get_chromosomes(self, obj) -> list:
        return ChromosomeSerializer(self._active_chromosomes(obj), many=True).data

    def get_summary(self, obj) -> dict:
        green = orange = red = unresolved_orange = 0
        for chromo in self._active_chromosomes(obj):
            sem = chromo.semaphore
            if sem == 'green':
                green += 1
            elif sem == 'orange':
                orange += 1
                if chromo.resolution_status != 'RESOLVED':
                    unresolved_orange += 1
            else:
                red += 1
        return {
            'total': green + orange + red,
            'green': green,
            'orange': orange,
            'red': red,
            'unresolved_orange': unresolved_orange,
            # RN-01/RN-02: hay naranjas sin resolver → no se puede emitir (P2)
            'is_blocked': unresolved_orange > 0 or red > 0,
        }


class AuditEventSerializer(serializers.ModelSerializer):
    """Evento de auditoría read-only (ADR-0022). Expone el actor por username."""

    actor_name = serializers.CharField(source='actor.get_full_name', default='', read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            'id', 'event_type', 'chromosome', 'actor', 'actor_name',
            'payload', 'created_at', 'previous_hash', 'current_hash',
        ]
        read_only_fields = fields
