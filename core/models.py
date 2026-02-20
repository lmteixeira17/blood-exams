"""
Models for the blood exams management system.
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile with health-relevant data."""

    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(
        null=True, blank=True,
        verbose_name='Data de Nascimento'
    )
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True,
        verbose_name='Sexo'
    )
    is_active_subscriber = models.BooleanField(
        default=True,
        verbose_name='Assinante Ativo',
        help_text='Para futura integração de pagamento'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Perfil do Usuário'
        verbose_name_plural = 'Perfis dos Usuários'

    def __str__(self):
        return f"Perfil de {self.user.get_full_name() or self.user.username}"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Biomarker(models.Model):
    """Reference catalog of blood test biomarkers."""

    name = models.CharField(
        max_length=200, unique=True,
        verbose_name='Nome',
        help_text='Ex: Hemoglobina, Colesterol Total'
    )
    code = models.CharField(
        max_length=50, unique=True,
        verbose_name='Código',
        help_text='Ex: HGB, CT, GLI'
    )
    unit = models.CharField(
        max_length=50,
        verbose_name='Unidade',
        help_text='Ex: g/dL, mg/dL, U/L'
    )
    ref_min_male = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Ref. Mín. Masculino'
    )
    ref_max_male = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Ref. Máx. Masculino'
    )
    ref_min_female = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Ref. Mín. Feminino'
    )
    ref_max_female = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Ref. Máx. Feminino'
    )
    category = models.CharField(
        max_length=100,
        verbose_name='Categoria',
        help_text='Ex: Hemograma, Lipidograma, Glicemia'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )
    aliases = models.TextField(
        blank=True,
        verbose_name='Nomes Alternativos',
        help_text='Nomes alternativos separados por vírgula para matching com IA'
    )

    class Meta:
        verbose_name = 'Biomarcador'
        verbose_name_plural = 'Biomarcadores'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.unit}"

    def get_ref_range(self, gender='M'):
        if gender == 'F':
            return (self.ref_min_female, self.ref_max_female)
        return (self.ref_min_male, self.ref_max_male)


class Exam(models.Model):
    """Uploaded blood exam file."""

    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('error', 'Erro'),
    ]

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('image', 'Imagem'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='exams',
        verbose_name='Usuário'
    )
    file = models.FileField(
        upload_to='exams/%Y/%m/',
        verbose_name='Arquivo'
    )
    file_type = models.CharField(
        max_length=10, choices=FILE_TYPE_CHOICES,
        verbose_name='Tipo de Arquivo'
    )
    exam_date = models.DateField(
        verbose_name='Data do Exame',
        help_text='Data em que o exame de sangue foi realizado'
    )
    lab_name = models.CharField(
        max_length=200, blank=True,
        verbose_name='Laboratório'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    ai_raw_response = models.TextField(
        blank=True,
        verbose_name='Resposta bruta da IA'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Mensagem de Erro'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Enviado em'
    )

    class Meta:
        verbose_name = 'Exame'
        verbose_name_plural = 'Exames'
        ordering = ['-exam_date', '-uploaded_at']
        indexes = [
            models.Index(fields=['user', '-exam_date']),
            models.Index(fields=['status']),
            models.Index(fields=['-uploaded_at']),
        ]

    def __str__(self):
        return f"Exame de {self.user.username} - {self.exam_date}"

    @property
    def result_count(self):
        return self.results.count()

    @property
    def abnormal_count(self):
        return self.results.filter(is_abnormal=True).count()

    @property
    def validation_status(self):
        """Overall validation status: 'clean', 'warnings', or 'errors'."""
        flags = self.validation_flags.filter(resolved=False)
        if flags.filter(severity='error').exists():
            return 'errors'
        if flags.filter(severity__in=['warning', 'auto_corrected']).exists():
            return 'warnings'
        return 'clean'

    @property
    def unresolved_flag_count(self):
        return self.validation_flags.filter(resolved=False).count()


class ExamResult(models.Model):
    """Individual biomarker value extracted from an exam."""

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='results',
        verbose_name='Exame'
    )
    biomarker = models.ForeignKey(
        Biomarker, on_delete=models.CASCADE,
        verbose_name='Biomarcador'
    )
    value = models.DecimalField(
        max_digits=12, decimal_places=4,
        verbose_name='Valor'
    )
    ref_min = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Ref. Mín. (do exame)'
    )
    ref_max = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name='Ref. Máx. (do exame)'
    )
    is_abnormal = models.BooleanField(
        default=False,
        verbose_name='Fora da Faixa'
    )

    class Meta:
        verbose_name = 'Resultado do Exame'
        verbose_name_plural = 'Resultados dos Exames'
        unique_together = ['exam', 'biomarker']
        ordering = ['biomarker__category', 'biomarker__name']
        indexes = [
            models.Index(fields=['exam', 'biomarker']),
            models.Index(fields=['is_abnormal']),
        ]

    def __str__(self):
        return f"{self.biomarker.name}: {self.value} {self.biomarker.unit}"

    def _get_standard_ref(self):
        """Get standard reference values from Biomarker catalog based on user gender."""
        try:
            gender = self.exam.user.profile.gender
        except Exception:
            gender = 'M'
        if gender == 'F':
            return (self.biomarker.ref_min_female, self.biomarker.ref_max_female)
        return (self.biomarker.ref_min_male, self.biomarker.ref_max_male)

    def save(self, *args, **kwargs):
        # Always use standard scientific reference values from Biomarker model
        std_min, std_max = self._get_standard_ref()
        self.ref_min = std_min
        self.ref_max = std_max

        # Auto-detect abnormal values
        if self.ref_min is not None and self.value < self.ref_min:
            self.is_abnormal = True
        elif self.ref_max is not None and self.value > self.ref_max:
            self.is_abnormal = True
        else:
            self.is_abnormal = False
        super().save(*args, **kwargs)

    @property
    def validation_status(self):
        """Validation status for this specific result."""
        flags = self.validation_flags.filter(resolved=False)
        if flags.filter(severity='error').exists():
            return 'error'
        if flags.filter(severity='warning').exists():
            return 'warning'
        if flags.filter(severity='auto_corrected').exists():
            return 'auto_corrected'
        if flags.filter(severity='info').exists():
            return 'info'
        return 'clean'


class AIAnalysis(models.Model):
    """AI-generated interpretation of exam results."""

    exam = models.OneToOneField(
        Exam, on_delete=models.CASCADE, related_name='analysis',
        verbose_name='Exame'
    )
    summary = models.TextField(
        verbose_name='Resumo Geral',
        help_text='Resumo geral da saúde baseado nos resultados'
    )
    alerts = models.JSONField(
        default=list,
        verbose_name='Alertas',
        help_text='Lista de valores preocupantes'
    )
    improvements = models.JSONField(
        default=list,
        verbose_name='Melhorias',
        help_text='Melhorias em relação a exames anteriores'
    )
    deteriorations = models.JSONField(
        default=list,
        verbose_name='Pioras',
        help_text='Pioras em relação a exames anteriores'
    )
    recommendations = models.TextField(
        verbose_name='Recomendações',
        help_text='Recomendações da IA'
    )
    comparison_text = models.TextField(
        blank=True,
        verbose_name='Comparação Histórica'
    )
    model_used = models.CharField(
        max_length=50,
        verbose_name='Modelo IA Utilizado'
    )
    input_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens de Entrada')
    output_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens de Saída')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Análise IA'
        verbose_name_plural = 'Análises IA'

    def __str__(self):
        return f"Análise do Exame {self.exam.exam_date} - {self.exam.user.username}"


class ExamValidation(models.Model):
    """Validation flags generated during exam processing."""

    SEVERITY_CHOICES = [
        ('info', 'Informativo'),
        ('warning', 'Atenção'),
        ('error', 'Erro'),
        ('auto_corrected', 'Corrigido Automaticamente'),
    ]

    CATEGORY_CHOICES = [
        ('physiological', 'Faixa Fisiológica'),
        ('cross_biomarker', 'Validação Cruzada'),
        ('wbc_percentage', 'Leucograma Percentual'),
        ('duplicate_exam', 'Exame Duplicado'),
        ('historical', 'Consistência Histórica'),
        ('low_confidence', 'Baixa Confiança IA'),
        ('unmatched', 'Biomarcador Não Identificado'),
    ]

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='validation_flags',
        verbose_name='Exame'
    )
    exam_result = models.ForeignKey(
        ExamResult, on_delete=models.CASCADE, null=True, blank=True,
        related_name='validation_flags',
        verbose_name='Resultado'
    )
    biomarker_code = models.CharField(max_length=50, verbose_name='Código do Biomarcador')
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES,
        verbose_name='Severidade'
    )
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES,
        verbose_name='Categoria'
    )
    message = models.TextField(verbose_name='Mensagem')
    original_value = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
        verbose_name='Valor Original'
    )
    corrected_value = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True,
        verbose_name='Valor Corrigido'
    )
    details = models.JSONField(default=dict, blank=True, verbose_name='Detalhes')
    resolved = models.BooleanField(default=False, verbose_name='Resolvido')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Flag de Validação'
        verbose_name_plural = 'Flags de Validação'
        ordering = ['-severity', 'biomarker_code']
        indexes = [
            models.Index(fields=['exam', 'severity']),
            models.Index(fields=['resolved']),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.biomarker_code}: {self.message[:80]}"


class BiomarkerTrendAnalysis(models.Model):
    """Cached AI-generated trend analysis for a biomarker's historical data."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='trend_analyses',
        verbose_name='Usuário'
    )
    biomarker = models.ForeignKey(
        Biomarker, on_delete=models.CASCADE, related_name='trend_analyses',
        verbose_name='Biomarcador'
    )
    analysis_text = models.TextField(verbose_name='Análise da Tendência')
    result_count = models.PositiveIntegerField(
        verbose_name='Qtd. Resultados',
        help_text='Número de resultados usados para gerar a análise (para invalidação de cache)'
    )
    model_used = models.CharField(max_length=50, verbose_name='Modelo IA Utilizado')
    input_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens de Entrada')
    output_tokens = models.PositiveIntegerField(default=0, verbose_name='Tokens de Saída')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Análise de Tendência'
        verbose_name_plural = 'Análises de Tendência'
        unique_together = ['user', 'biomarker']
        indexes = [
            models.Index(fields=['user', 'biomarker']),
        ]

    def __str__(self):
        return f"Tendência {self.biomarker.name} - {self.user.username}"
