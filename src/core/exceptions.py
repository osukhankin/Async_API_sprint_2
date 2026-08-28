class ElasticsearchUnavailableError(Exception):
    """Elasticsearch недоступен после исчерпания повторных попыток."""
