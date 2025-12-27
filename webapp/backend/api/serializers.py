"""Serializers for API requests and responses."""

from rest_framework import serializers


class GenerateRequestSerializer(serializers.Serializer):
    """Serializer for generate request."""

    prompt = serializers.CharField(required=True, allow_blank=False)
    provider = serializers.CharField(default="auto")
    model = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    temperature = serializers.FloatField(default=0.0)
    seed = serializers.IntegerField(required=False, allow_null=True)
    api_key = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    base_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    output_format = serializers.CharField(default="markdown")
    verbose = serializers.BooleanField(default=True)
    resume = serializers.BooleanField(default=False)
    checkpoint_dir = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cache_dir = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    no_cache = serializers.BooleanField(default=False)


class GenerateResponseSerializer(serializers.Serializer):
    """Serializer for generate response."""

    job_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()


class GenerateResultSerializer(serializers.Serializer):
    """Serializer for generate result."""

    job_id = serializers.CharField()
    status = serializers.CharField()
    result = serializers.CharField(required=False, allow_null=True)
    intermediate_outputs = serializers.DictField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)


class AnalyzeRequestSerializer(serializers.Serializer):
    """Serializer for analyze request."""

    codebase_path = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mode = serializers.CharField(default="full")
    depth = serializers.CharField(default="high")
    provider = serializers.CharField(default="auto")
    model = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    temperature = serializers.FloatField(default=0.0)
    api_key = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    base_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class AnalyzeResponseSerializer(serializers.Serializer):
    """Serializer for analyze response."""

    job_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()


class AnalyzeResultSerializer(serializers.Serializer):
    """Serializer for analyze result."""

    job_id = serializers.CharField()
    status = serializers.CharField()
    result = serializers.DictField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)


class ConfigSerializer(serializers.Serializer):
    """Serializer for configuration."""

    provider = serializers.CharField(required=False)
    model = serializers.CharField(required=False, allow_null=True)
    temperature = serializers.FloatField(required=False)
    seed = serializers.IntegerField(required=False, allow_null=True)
    base_url = serializers.CharField(required=False, allow_null=True)
    api_key = serializers.CharField(required=False, allow_null=True)
    verbose = serializers.BooleanField(required=False)
    output_format = serializers.CharField(required=False)
    checkpoint_dir = serializers.CharField(required=False, allow_null=True)
    cache_dir = serializers.CharField(required=False, allow_null=True)


class ProgressUpdateSerializer(serializers.Serializer):
    """Serializer for progress updates."""

    job_id = serializers.CharField()
    stage = serializers.CharField()
    message = serializers.CharField()
    progress = serializers.FloatField()
    current = serializers.IntegerField(required=False, allow_null=True)
    total = serializers.IntegerField(required=False, allow_null=True)

